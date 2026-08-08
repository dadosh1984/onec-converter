"""MCP-сервер onec-converter: пайплайн переноса данных между ИБ 1С.

Пайплайн: init → inspect_source → extract → inspect_target → map → transform
          → prevalidate → preview → load → verify
Правило «1→1»: привязка пары источник→приёмник в проекте, блокировка загрузки
при несовпадении. Кеш: повторный inspect/extract не перечитывает базу.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .base_reader import Base77
from .cache import Cache, file_key
from .inspect_target import ProjectBinding, inspect_target_from_http
from .intermediate import OBJ_TYPE, save_json_batch
from .mapping import build_prompt, validate_rules
from .validate import validate_batch

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
    last_step: str | None = None
    cache_hits: int = 0

    # ---- шаги пайплайна (чистые функции; MCP-тулы — обёртки ниже) ----

    def _mark(self, step: str) -> None:
        self.last_step = step

    def step_init(self, project_dir: str, source_ib_id: str, target_ib_id: str,
                  source_dir: str) -> dict[str, Any]:
        self.project_dir = Path(project_dir)
        self.binding = ProjectBinding.create(self.project_dir, source_ib_id, target_ib_id)
        self.source = Base77(Path(source_dir))
        self._mark('init')
        return {'ok': True, 'binding': {'source': source_ib_id, 'target': target_ib_id}}

    def step_inspect_source(self) -> dict[str, Any]:
        if self.source is None:
            raise ValueError('вызовите init')
        key = file_key(self.source.dat_path)
        cached = self.cache.get_json(key, 'metadata.json')
        if cached is not None:
            self.cache_hits += 1
            self._mark('inspect_source')
            return {'ok': True, 'cached': True, 'metadata': cached}
        reader = self.source.data
        meta = {
            'sections': reader.sections(),
            'unique_ids': reader.unique_ids(),
            'constants': len(reader.constants()),
            'references_tables': len(reader.references()),
        }
        self.cache.put_json(key, 'metadata.json', meta)
        self._mark('inspect_source')
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
        self._mark('extract')
        save_json_batch(objs, out_file)
        return {'ok': True, 'objects': len(objs), 'file': out_file}

    def step_inspect_target(self, target_metadata: dict[str, Any]) -> dict[str, Any]:
        tm = inspect_target_from_http(target_metadata)
        self._mark('inspect_target')
        return {'ok': True, 'objects': len(tm.objects)}

    def step_map(self, meta_source: dict[str, Any], meta_target: dict[str, Any],
                 rules: dict[str, Any]) -> dict[str, Any]:
        errors = validate_rules(rules)
        if errors:
            return {'ok': False, 'errors': errors}
        self.rules = rules
        self._mark('map')
        return {'ok': True, 'prompt': build_prompt(meta_source, meta_target),
                'rules': rules}

    def step_prevalidate(self) -> dict[str, Any]:
        vr = validate_batch(self.extracted)
        self._mark('prevalidate')
        return {'ok': vr.ok, 'errors': vr.errors, 'warnings': vr.warnings,
                'counts': vr.counts}

    def step_load(self, http_load: Callable[[list[dict[str, Any]], str, str], dict[str, Any]]) -> dict[str, Any]:
        # http_load — функция(пакет) -> результат; приёмник загружается через HTTP-клиент
        if self.binding is None:
            raise ValueError('вызовите init')
        results = []
        for obj in self.extracted:
            results.append(http_load([obj], self.binding.source_ib_id, self.binding.target_ib_id))
        self._mark('load')
        ok_all = all(bool(r.get('ok')) for r in results)
        created = sum(int(r.get('created', 0)) for r in results)
        return {'ok': ok_all, 'created': created}

    def step_status(self) -> dict[str, Any]:
        """Состояние коннекторов, кеша и последнего шага пайплайна."""
        connectors: dict[str, Any] = {
            'file': {'configured': self.source is not None,
                     'path': str(self.source.dat_path) if self.source else None},
            'http': {'configured': False},
            'sql': {'configured': False},
        }
        entries = 0
        bytes_total = 0
        if self.cache.root.is_dir():
            for d in self.cache.root.iterdir():
                if not d.is_dir():
                    continue
                for f in d.iterdir():
                    if f.is_file():
                        entries += 1
                        bytes_total += f.stat().st_size
        return {'ok': True,
                'connectors': connectors,
                'cache': {'entries': entries, 'bytes': bytes_total,
                          'hits': self.cache_hits, 'root': str(self.cache.root)},
                'last_step': self.last_step,
                'binding': {'source': self.binding.source_ib_id,
                            'target': self.binding.target_ib_id}
                if self.binding else None}

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
    """Статус пайплайна переноса: коннекторы, кеш, последний шаг (точка входа для LLM)."""
    state = PipelineState(Path('.'))
    return json.dumps(state.step_status(), ensure_ascii=False)


@mcp.tool()
def tools() -> list[dict[str, Any]]:
    """Список тулов пайплайна (точка входа для LLM-агента)."""
    return PipelineState(Path('.')).tools()
