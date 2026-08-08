"""Фаза 32: дефекты по итогам внешнего анализа (0.15.0)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from onec_converter.cache import Cache, file_key
from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd

F = [FixtureField('_VERSION', 'RV', length=16),
     FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]


def _fake_db(tmp_path: Path) -> Path:
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE1', fields=F, rows=[])]))
    return src


# ---- 1/2. clone_db: кеш-инвалидация до перезаписи ----
def test_clone_db_cache_drop_before_overwrite(tmp_path: Path):
    from onec_converter.clone_db import clone_db

    src = tmp_path / 'src'
    src.mkdir()
    cd = src / '1Cv8.1CD'
    cd.write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE1', fields=F, rows=[])]))
    tgt = tmp_path / 'tgt'

    # 1-е клонирование создаёт dst; до повторного кладём кеш под его ключ
    rep = clone_db(str(src), str(tgt))
    dst = Path(rep['target'])
    key1 = file_key(dst)
    c = Cache()
    c.put(key1, 'meta', b'OLD-META')  # кеш по НЕПЕРЕЗАПИСАННОМУ dst
    assert c.has(key1, 'meta')

    # источник изменился (другая структура)
    cd.write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE10', fields=F, rows=[])]))

    # повторное клонирование в тот же target_dir: старый ключ дропнут
    clone_db(str(src), str(tgt))
    key2 = file_key(dst)
    assert not c.has(key1, 'meta')  # старый кеш по прежнему файлу сброшен
    assert key2 != key1  # у нового dst новый ключ (нет в кеше)


# ---- 2. base_health: include_rows/sample_tables ----
def test_health_default_no_rows(tmp_path: Path):
    from onec_converter.health import base_health

    h = base_health(_fake_db(tmp_path))
    assert h['ok'] and h['rows_computed'] is False
    assert h['rows'] == -1  # health-пинг не читает данные
    assert h['tables'] >= 1


def test_health_include_rows(tmp_path: Path):
    from onec_converter.health import base_health

    h = base_health(_fake_db(tmp_path), include_rows=True)
    assert h['rows_computed'] is True and h['rows'] >= 0


def test_health_sample_tables(tmp_path: Path):
    from onec_converter.health import base_health

    h = base_health(_fake_db(tmp_path), include_rows=True, sample_tables=1)
    assert h['rows_computed'] is True and h['rows'] >= 0


# ---- 3. audit: flush/close/ротация ----
def test_audit_buffered_and_flush(tmp_path: Path):
    from onec_converter.audit import AuditLog, read_audit

    path = tmp_path / 'a.jsonl'
    log = AuditLog(path, file_flush=2)  # flush через каждые 2 записи
    log.info('extract', obj='Документ.X')
    assert read_audit(path) == []  # буфер не сброшен (1 < file_flush)
    log.warning('transform', obj='Y')  # 2-я запись → flush
    assert len(read_audit(path)) == 2
    log.close()
    log.close()  # idempotent
    assert len(read_audit(path)) == 2


def test_audit_rotation(tmp_path: Path):
    from onec_converter.audit import AuditLog, read_audit

    path = tmp_path / 'a.jsonl'
    # много записей одной сессией: файл перерастает лимит
    log = AuditLog(path, max_bytes=200)
    for i in range(20):
        log.info('load', obj=f'OBJ-{i}')
    log.close()
    assert read_audit(path)  # все записи на месте
    # при новом открытии файл > max_bytes → ротация в .1
    log2 = AuditLog(path, max_bytes=200)
    log2.info('load', obj='NEW')
    log2.close()
    assert path.with_suffix(path.suffix + '.1').is_file()
    assert read_audit(path)  # основной журнал продолжает работать


# ---- 4. notify: retry с backoff ----
def test_notify_retry_on_urlerror(monkeypatch):
    import urllib.error

    from onec_converter import notify as n

    calls: list[str] = []
    fake_resp = type('Resp', (), {'__enter__': lambda s: s,
                                  '__exit__': lambda *a: False,
                                  'status': 200})()

    def flaky(*args, **kw):
        calls.append(args[0])
        if len(calls) < 3:
            raise urllib.error.URLError('boom')
        return fake_resp

    monkeypatch.setattr('urllib.request.urlopen', flaky)
    monkeypatch.setattr(n.time, 'sleep', lambda s: None)
    resp = n.send_webhook('http://h', {'x': 1}, attempts=3, backoff=0.01)
    assert resp['ok'] and resp['status'] == 200
    assert len(calls) == 3  # две неудачи + успех


def test_notify_retry_exhausted(monkeypatch):
    import urllib.error

    from onec_converter import notify as n

    def fail(*args, **kw):
        raise urllib.error.URLError('boom')

    monkeypatch.setattr('urllib.request.urlopen', fail)
    monkeypatch.setattr(n.time, 'sleep', lambda s: None)
    with pytest.raises(n.NotifyError, match='попыток'):
        n.send_webhook('http://h', {'x': 1}, attempts=2, backoff=0.01)


def test_notify_http_error_not_retried(monkeypatch):
    import urllib.error

    from onec_converter import notify as n

    calls = []

    def http_err(*args, **kw):
        calls.append(1)
        raise urllib.error.HTTPError('h', 403, 'denied', {}, None)

    monkeypatch.setattr('urllib.request.urlopen', http_err)
    resp = n.send_webhook('http://h', {'x': 1}, attempts=3)
    assert resp == {'ok': False, 'status': 403}
    assert len(calls) == 1  # 4xx не ретраится


# ---- 5. openapi: bearerAuth + соответствие путям ----
def test_openapi_bearer_auth():
    doc = yaml.safe_load(Path('docs/openapi.yaml')
                         .read_text(encoding='utf-8'))
    schemes = doc['components']['securitySchemes']
    assert 'BearerAuth' in schemes
    assert schemes['BearerAuth']['type'] == 'http'
    assert schemes['BearerAuth']['scheme'] == 'bearer'
    # /load поддерживает Bearer (JWT), /metadata — только apiKey
    sec = doc['paths']['/load']['post'].get('security', [])
    assert {'BearerAuth': []} in sec


def test_openapi_matches_real_paths():
    # пути спеки соответствуют реальным эндпоинтам http_client
    import re

    http = Path('src/onec_converter/http_client.py').read_text(encoding='utf-8')
    real = sorted(re.findall(r"_request\('(?:GET|POST)',\s*'([^']+)'", http))
    doc = yaml.safe_load(Path('docs/openapi.yaml')
                         .read_text(encoding='utf-8'))
    spec_paths = sorted(doc['paths'])
    assert real == spec_paths


# ---- 6. extract: потоковое сохранение (save_json_stream) ----
def test_extract_uses_streaming(monkeypatch, tmp_path: Path):
    """cmd_extract сохраняет через save_json_stream, а не batch."""
    src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    assert 'save_json_stream(objs, args.out)' in src
    assert 'save_json_batch(objs, args.out)' not in src


def test_save_json_stream_roundtrip(tmp_path: Path):
    from onec_converter.intermediate import load_json_batch, save_json_stream

    p = tmp_path / 'out.json'
    save_json_stream([{'a': 1}, {'b': 2}, {'c': 3}], p)
    assert load_json_batch(p) == [{'a': 1}, {'b': 2}, {'c': 3}]
    # частичное содержимое (генератор) не держит всё в памяти
    def gen():
        for i in range(1000):
            yield {'i': i}
    p2 = tmp_path / 'out2.json'
    save_json_stream(gen(), p2)
    assert len(load_json_batch(p2)) == 1000


# ---- 7. cache: TTL-эвикция удаляет, get/has не возвращают ----
def test_cache_ttl_eviction(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    key = 'abc'
    c.put_json(key, 'meta', {'v': 1})
    assert c.has(key, 'meta')
    # состариваем файл
    p = c.get(key, 'meta')
    assert p is not None
    old = time.time() - 10_000
    p.touch()  # mtime обновится на now
    import os
    os.utime(p, (old, old))
    removed = c.trim(ttl_seconds=3600)
    assert removed >= 1
    assert not c.has(key, 'meta')
    assert c.get(key, 'meta') is None
    assert c.get_json(key, 'meta') is None
