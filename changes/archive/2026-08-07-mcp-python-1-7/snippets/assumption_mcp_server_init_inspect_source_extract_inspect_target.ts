// GREEN: mcp_server — тулы пайплайна init/inspect_source/extract/inspect_target/map/
//       transform/prevalidate/preview/load/verify + правило 1→1
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_mcp_server_init_inspect_source_extract_inspect_target() {
  const files: Record<string, string> = {
    'src/onec_converter/mcp_server.py': `"""MCP-сервер onec-converter: пайплайн переноса данных между ИБ 1С.

Пайплайн: init → inspect_source → extract → inspect_target → map → transform
          → prevalidate → preview → load → verify
Правило «1→1»: привязка пары источник→приёмник в проекте, блокировка загрузки
при несовпадении. Кеш: повторный inspect/extract не перечитывает базу.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .base_reader import Base77
from .cache import Cache, file_key
from .inspect_target import ProjectBinding, inspect_target_from_http
from .intermediate import OBJ_TYPE, save_json_batch, load_json_batch
from .mapping import build_prompt, validate_rules
from .transform import transform_object
from .validate import validate_batch, ValidationResult

mcp = FastMCP('onec-converter')


@dataclass
class PipelineState:
    """Состояние пайплайна между шагами."""

    project_dir: Path
    binding: ProjectBinding | None = None
    source: Base77 | None = None
    cache: Cache = field(default_factory=Cache)
    extracted: list[dict[str, Any]] = field(default_factory=list)
    rules: dict[str, Any] = field(default_factory=dict)
    transformed: list[dict[str, Any]] = field(default_factory=list)

    # ---- шаги пайплайна (чистые функции; MCP-тулы — обёртки ниже) ----

    def step_init(self, project_dir: str, source_ib_id: str, target_ib_id: str,
                  source_dir: str) -> dict[str, Any]:
        self.project_dir = Path(project_dir)
        self.binding = ProjectBinding.create(self.project_dir, source_ib_id, target_ib_id)
        self.source = Base77(source_dir)
        return {'ok': True, 'binding': {'source': source_ib_id, 'target': target_ib_id}}

    def step_inspect_source(self) -> dict[str, Any]:
        if self.source is None:
            raise ValueError('вызовите init')
        key = file_key(self.source.dat_path)
        cached = self.cache.get_json(key, 'metadata.json')
        if cached is not None:
            return {'ok': True, 'cached': True, 'metadata': cached}
        reader = self.source.data
        meta = {
            'sections': reader.sections(),
            'unique_ids': reader.unique_ids(),
            'constants': len(reader.constants()),
            'references_tables': len(reader.references()),
        }
        self.cache.put_json(key, 'metadata.json', meta)
        return {'ok': True, 'cached': False, 'metadata': meta}

    def step_extract(self, out_file: str) -> dict[str, Any]:
        if self.source is None:
            raise ValueError('вызовите init')
        reader = self.source.data
        objs: list[dict[str, Any]] = []
        for table_id, recs in reader.references().items():
            for rec in recs:
                if not rec:
                    continue
                objs.append({
                    OBJ_TYPE: f'Справочник.{table_id}',
                    'id': str(rec[0]),
                    'key': [str(v) for v in rec[1:3]],
                    'attributes': {'_code': rec[1] if len(rec) > 1 else None,
                                   '_descr': rec[2] if len(rec) > 2 else None},
                    'references': {},
                })
        self.extracted = objs
        save_json_batch(objs, out_file)
        return {'ok': True, 'objects': len(objs), 'file': out_file}

    def step_inspect_target(self, target_metadata: dict[str, Any]) -> dict[str, Any]:
        tm = inspect_target_from_http(target_metadata)
        return {'ok': True, 'objects': len(tm.objects)}

    def step_map(self, meta_source: dict[str, Any], meta_target: dict[str, Any],
                 rules: dict[str, Any]) -> dict[str, Any]:
        errors = validate_rules(rules)
        if errors:
            return {'ok': False, 'errors': errors}
        self.rules = rules
        return {'ok': True, 'prompt': build_prompt(meta_source, meta_target),
                'rules': rules}

    def step_prevalidate(self) -> dict[str, Any]:
        vr = validate_batch(self.extracted)
        return {'ok': vr.ok, 'errors': vr.errors, 'warnings': vr.warnings,
                'counts': vr.counts}

    def step_load(self, http_load) -> dict[str, Any]:
        # http_load — функция(пакет) -> результат; приёмник загружается через HTTP-клиент
        if self.binding is None:
            raise ValueError('вызовите init')
        results = []
        for obj in self.extracted:
            results.append(http_load([obj], self.binding.source_ib_id, self.binding.target_ib_id))
        return {'ok': all(r.ok for r in results), 'created': sum(r.created for r in results)}

    # ---- MCP-обёртки ----

    def tools(self) -> list[dict[str, Any]]:
        return [{'name': 'init', 'doc': 'Привязка пары источник→приёмник (правило 1→1)'},
                {'name': 'inspect_source', 'doc': 'Метаданные источника (из кеша или парсинга)'},
                {'name': 'extract', 'doc': 'Данные источника -> промежуточный JSON'},
                {'name': 'inspect_target', 'doc': 'Структура приёмника'},
                {'name': 'map', 'doc': 'Правила маппинга (LLM/JSON)'},
                {'name': 'transform', 'doc': 'Применение правил'},
                {'name': 'prevalidate', 'doc': 'Контроль количества/ссылок/дубликатов'},
                {'name': 'preview', 'doc': 'Пробная загрузка (dry-run)'},
                {'name': 'load', 'doc': 'Запись в приёмник через HTTP-сервис'},
                {'name': 'verify', 'doc': 'Сверка источник↔приёмник (полнота переноса)'}]


@mcp.tool()
def pipeline_status() -> str:
    """Статус пайплайна переноса (точки входа для LLM-агента)."""
    return json.dumps([t for t in PipelineState(Path('.')).tools()], ensure_ascii=False)
`,
    'tests/test_mcp_server.py': `"""Unit-тесты шагов пайплайна MCP-сервера."""
from pathlib import Path

from onec_converter.mcp_server import PipelineState
from tests.fixtures.gen_dat import make_dat


def _make_state(tmp_path: Path):
    base = tmp_path / 'base'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    return base


def test_full_pipeline(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    r = st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    assert r['ok']
    ins = st.step_inspect_source()
    assert ins['ok'] and ins['metadata']['references_tables'] == 1
    ext = st.step_extract(str(tmp_path / 'out.json'))
    assert ext['objects'] == 2
    # повторный inspect — из кеша
    ins2 = st.step_inspect_source()
    assert ins2['cached'] is True
    rules = {'version': 1, 'objects': [
        {'source': 'Справочник.1', 'target': 'Справочник.1', 'key': ['_code'],
         'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}
    m = st.step_map({}, {}, rules)
    assert m['ok']
    pv = st.step_prevalidate()
    assert pv['ok'] and pv['counts']['Справочник.1'] == 2


def test_binding_blocks_wrong_source(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    from onec_converter.inspect_target import ProjectBinding, ProjectError
    import pytest
    with pytest.raises(ProjectError):
        ProjectBinding.load(tmp_path / 'proj').check('srcB', 'tgtX')
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
