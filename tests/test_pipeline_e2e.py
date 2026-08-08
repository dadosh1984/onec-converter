"""Фаза 7: сквозной перенос 7.7→8.3 (интеграция пайплайна).

Полный путь: Base77 (1Cv77.dat, cp866/cp1251) → intermediate JSON →
TOON-правила → transform → validate → HTTP-загрузка в приёмник 8.3
(httpx MockTransport — реальные базы не изменяются, read-only).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from onec_converter.base_reader import Base77
from onec_converter.http_client import HttpClient83
from onec_converter.intermediate import OBJ_ATTRS, OBJ_KEY, OBJ_TYPE
from onec_converter.transform import transform_object
from onec_converter.validate import validate_batch
from tests.fixtures.gen_dat import make_dat

# Правила TOON: справочник 7.7 (id=1) -> справочник 8.3 «Банки»
RULES = {'version': 1, 'objects': [
    {'source': 'Справочник.1', 'target': 'Справочник.Банки', 'key': ['Код'],
     'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}


def _base77(tmp_path: Path, encoding: str = 'cp866') -> Base77:
    base = tmp_path / f'base_{encoding}'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    if encoding == 'cp1251':
        refs = [['1|', '00001', 'Товар «Ковёр»'], ['2|', '00002', 'Наименование: №5']]
    else:
        # cp866 не содержит « » и строчной ё — используем совместимый текст
        refs = [['1|', '00001', 'Товар Ковер'], ['2|', '00002', 'Наименование 5']]
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2}, references={1: refs}, encoding=encoding))
    return Base77(base, encoding=encoding)


def _received() -> list[dict]:
    """Собранные payload'и POST /load (имитация приёмника 8.3)."""
    return []


def _mock_transport(received: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == 'GET' and request.url.path == '/metadata':
            return httpx.Response(200, json={'ok': True, 'objects': []})
        if request.method == 'POST' and request.url.path == '/load':
            payload = json.loads(request.content.decode('utf-8'))
            received.append(payload)
            return httpx.Response(201, json={'created': len(payload['objects']),
                                             'updated': 0, 'errors': []})
        return httpx.Response(404, json={'error': 'not found'})
    return httpx.MockTransport(handler)


def _transform(objs: list[dict]) -> list[dict]:
    out = []
    for obj in objs:
        rule = RULES['objects'][0]
        tgt = transform_object(obj, rule, resolver=None)  # type: ignore[arg-type]
        out.append(tgt)
    return out


def test_e2e_77_83_cp866(tmp_path: Path):
    """Сквозной перенос 7.7 (cp866) → 8.3: извлечение, правила, валидация, HTTP."""
    src = _base77(tmp_path)
    # 1. извлечение (как step_extract)
    objs = []
    for table_id, recs in src.data.references().items():
        for rec in recs:
            objs.append({OBJ_TYPE: f'Справочник.{table_id}',
                         'id': str(rec[0]),
                         'key': [str(v) for v in rec[1:3]],
                         OBJ_ATTRS: {'_code': rec[1] if len(rec) > 1 else None,
                                     '_descr': rec[2] if len(rec) > 2 else None},
                         'references': {}})
    assert len(objs) == 2
    # 2. валидация до загрузки
    vr = validate_batch(objs)
    assert vr.ok and vr.counts.get('Справочник.1') == 2
    # 3. transform по правилам TOON
    tgt = _transform(objs)
    assert {o['type'] for o in tgt} == {'Справочник.Банки'}
    assert tgt[0][OBJ_ATTRS]['Код'] == '00001'
    assert tgt[0][OBJ_ATTRS]['Наименование'] == 'Товар Ковер'
    # 4. загрузка в приёмник 8.3 через HTTP-mock
    received = _received()
    async def run() -> list:
        client = HttpClient83('http://target:8080', transport=_mock_transport(received))
        try:
            return await client.load(tgt, 'srcA', 'tgtX')
        finally:
            await client.aclose()
    results = asyncio.run(run())
    assert all(r.ok for r in results)
    assert sum(r.created for r in results) == 2
    assert len(received) == 1
    payload = received[0]
    assert payload['source_ib'] == 'srcA' and payload['target_ib'] == 'tgtX'
    # кириллица дошла без искажений (UTF-8)
    names = [o['attributes']['Наименование'] for o in payload['objects']]
    assert names == ['Товар Ковер', 'Наименование 5']


def test_e2e_77_83_cp1251(tmp_path: Path):
    """Сквозной перенос CP1251: cp1251 → UTF-8 до приёмника (A4 middleware)."""
    src = _base77(tmp_path, encoding='cp1251')
    refs = src.data.references()[1]
    assert refs[0][2] == 'Товар «Ковёр»'
    received = _received()
    async def run() -> None:
        client = HttpClient83('http://target:8080', transport=_mock_transport(received))
        try:
            await client.load([{OBJ_TYPE: 'Справочник.Банки', 'id': '1|',
                                OBJ_KEY: ['00001', refs[0][2]],
                                OBJ_ATTRS: {'Код': refs[0][1],
                                            'Наименование': refs[0][2]},
                                'references': {}}], 'srcA', 'tgtX')
        finally:
            await client.aclose()
    asyncio.run(run())
    name = received[0]['objects'][0]['attributes']['Наименование']
    assert name == 'Товар «Ковёр»'  # UTF-8, не «кракозябры»


def test_http_load_rejects_bad_pair(tmp_path: Path):
    """Контроль: приёмник отклоняет чужую пару (правило 1→1) — 409."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={'error': 'pair mismatch'})

    async def run() -> None:
        client = HttpClient83('http://target:8080', retries=1,
                              transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(Exception):
                await client.load([{}], 'srcA', 'tgtX')  # type: ignore[list-item]
        finally:
            await client.aclose()
    asyncio.run(run())


def test_migrate_tool_steps(tmp_path: Path):
    """MCP-тул migrate: последовательность шагов пайплайна с прогрессом."""
    from onec_converter.mcp_server import migrate

    src = _base77(tmp_path)
    proj = tmp_path / 'proj'
    rules = json.dumps(RULES, ensure_ascii=False)
    # порт 1 закрыт — load упадёт, но все шаги до него должны пройти
    res = json.loads(migrate(str(proj), 'srcA', 'tgtX', str(src.base_dir),
                             'http://127.0.0.1:1', rules=rules))
    names = [s['name'] for s in res['steps']]
    assert names == ['init', 'inspect_source', 'extract', 'map',
                     'transform', 'prevalidate', 'load']
    # все шаги до load успешны
    assert all(s['ok'] for s in res['steps'][:6])
    assert res['ok'] is False and 'load' in names
    # validate_rules не пропускает битые правила
    res_bad = json.loads(migrate(str(proj), 'srcA', 'tgtX', str(src.base_dir),
                                 'http://127.0.0.1:1', rules='{"version": 1}'))
    assert res_bad['ok'] is False
    names_bad = [s['name'] for s in res_bad['steps']]
    assert 'map' in names_bad and 'transform' not in names_bad
