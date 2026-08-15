"""MCP-сервер onec-converter: пайплайн переноса данных между ИБ 1С.

Пайплайн: init → inspect_source → extract → inspect_target → map → transform
          → prevalidate → preview → load → verify
Правило «1→1»: привязка пары источник→приёмник в проекте, блокировка загрузки
при несовпадении. Кеш: повторный inspect/extract не перечитывает базу.

Видимость в терминале: каждое применение команды пишется в stderr
([onec-converter …] ▶/✔/✘ имя(аргументы)) — видно в терминале сервера
и в TUI MCP-клиентов. Ответ каждого тула содержит `next` — рекомендуемую
следующую команду плейбука (см. docs/playbook.md), чтобы агент
продолжал работу по универсальной последовательности.
"""

from __future__ import annotations

import asyncio
import functools
import json
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# MCP SDK / pydantic-settings печатает в stderr предупреждение про
# неразрешённую forward-reference ('lifespan'), которое путает MCP-клиентов
# (pi/Claude читают stderr процесса, а баннер сервера должен быть первым и
# единственным сообщением). Подавляем его только для этой категории.
try:
    warnings.filterwarnings(
        'ignore',
        message='.*Field .lifespan. has an incomplete definition.*',
        module=r'pydantic_settings\.sources')
except Exception:  # noqa: S110,BLE001 — фильтр никогда не роняет импорт
    pass

from mcp.server.fastmcp import FastMCP

from .audit import get_audit
from .base_reader import Base77
from .cache import Cache, file_key
from .inspect_target import ProjectBinding, inspect_target_from_http
from .intermediate import OBJ_TYPE, save_json_batch
from .mapping import build_prompt, validate_rules
from .terminal import now_ms, tool_error, tool_finished, tool_started, tool_summary
from .timings import GLOBAL as GLOBAL_TIMINGS
from .validate import validate_batch

mcp = FastMCP('onec-converter')
# serverInfo.version отдаём НАШ version-релиз (а не версию MCP SDK), чтобы
# любой MCP-клиент (Claude/Cursor/pi/др.) видел версию инструмента по
# стандарту (поле serverInfo ответа initialize). Поле приватное, берём с
# защитой: на другой версии SDK даём __version__ через атрибут.
from . import __version__ as _VERSION

_vsrv = getattr(mcp, '_mcp_server', None)
if _vsrv is not None:
    try:
        _vsrv.version = _VERSION
    except Exception as exc:  # noqa: BLE001 — не роняем сервер из-за version
        print(f'[onec-converter] не вышло задать serverInfo.version: {exc}',
              file=__import__('sys').stderr, flush=True)

# Универсальная последовательность команд переноса (плейбук). Поле `next`
# в ответах тулов ведёт агента по этим шагам; тул playbook() возвращает
# полный список (см. docs/playbook.md).
PLAYBOOK: list[dict[str, str]] = [
    {'step': '1', 'command': 'tools()',
     'goal': 'Список доступных команд сервера'},
    {'step': '2', 'command': 'pipeline_status()',
     'goal': 'Состояние пайплайна: коннекторы, кеш, последний шаг, timings'},
    {'step': '3', 'command': "search_schema(source_dir, '<имя объекта>')",
     'goal': 'Найти таблицы метаданных по имени/синониму (например «Зарплат»)'},
    {'step': '4', 'command': 'base_health(source_dir)',
     'goal': 'Здоровье базы: версия, таблицы/строки, блокировки, место'},
    {'step': '5', 'command': "table_sizes(source_dir, '<фильтр>')",
     'goal': 'Оценить объём: строки и байты по таблицам (что переносить)'},
    {'step': '6', 'command': 'compare_structures(source_dir, target_dir)',
     'goal': 'Расхождения структур: только в источнике/приёмнике, разные типы'},
    {'step': '7', 'command': 'explain_diff(source_dir, target_dir)',
     'goal': 'Причины расхождений структур двух баз'},
    {'step': '8', 'command': 'auto_map_schemas(source_dir, target_dir)',
     'goal': 'Автогенерация TOON-правил маппинга по именам/синонимам'},
    {'step': '9', 'command': 'query_sql(source_dir, table, where, limit)',
     'goal': 'Выборочная проверка данных (пример записи, контроль условий)'},
    {'step': '10', 'command': 'compress_metadata(source_dir)',
     'goal': 'Краткое саммари метаданных для LLM (экономия токенов)'},
    {'step': '11',
     'command': "migrate(project_dir, source_ib_id, target_ib_id, source_dir, "
                "target_url, rules='{}', out_file='', source_encoding='cp866')",
     'goal': 'СКВОЗНОЙ перенос одной командой: init→inspect→extract→map→'
             'transform→prevalidate→load (шаги выполняются внутри migrate)'},
    {'step': '12',
     'command': 'load_direct(target_dir, input_file, workdir)',
     'goal': 'Прямая запись объектов в КОПИЮ 1Cv8.1CD приёмника (без HTTP)'},
    {'step': '13', 'command': 'guid_diff(source_dir, target_dir)',
     'goal': 'Сверка двух баз по GUID: полнота переноса объектов и таблиц'},
    {'step': '14', 'command': 'audit_verify(audit_file)',
     'goal': 'Проверка целостности audit-журнала (tamper-evident chain)'},
    {'step': '15', 'command': 'config_versions(source_dir)',
     'goal': 'Версии конфигурации: формат, ИБ/платформа, дифф CONFIG↔CONFIGSAVE'},
    {'step': '16', 'command': 'dump_metadata(source_dir)',
     'goal': 'Дамп метаданных базы в git-дружественный текст'},
    {'step': '17', 'command': 'cache_stats()',
     'goal': 'Метрики дискового кеша: файлы, байты, самый старый артефакт'},
    {'step': '18', 'command': 'pipeline_status()',
     'goal': 'Итоговое состояние пайплайна + метрики времени'},
]


def _playbook_summary() -> str:
    return ' → '.join(p['command'].split('(')[0] for p in PLAYBOOK)


def _current_role() -> str:
    """Роль MCP-клиента: env ONEC_MCP_ROLE (inspect|load), по умолчанию 'load'
    (максимальная, backward-compat) если переменная пустая/не задана."""
    import os

    return os.environ.get('ONEC_MCP_ROLE', 'load') or 'load'


def _require_role(role: str, tool: str) -> None:
    """Проверка роли клиента для опасного тула (RBAC, Фаза 37).

    Роль 'load' — полный доступ; 'inspect' — только чтение. Если
    недостаточно — поднимает RbacError с понятным сообщением.
    """
    got = _current_role()
    if role == 'load' and got != 'load':
        raise RbacError(
            f'тул {tool} требует роль load, а клиент: {got}. '
            f'Задайте ONEC_MCP_ROLE=load или используйте read-only тулы.')


class RbacError(Exception):
    """Недостаточно прав роли MCP-клиента."""


def _server_meta() -> dict[str, object]:
    """Метаданные сервера для встраивания в ответ каждого тула.
    server_version — установленный релиз; update — при наличии новой версии
    на PyPI. Вычисляется один раз на процесс, далее кэшируется в памяти;
    сетевой прост к PyPI не чаще раза в сутки (version_check)."""
    from .server_state import get_server_state
    from .version_check import _is_newer, current_version

    state = get_server_state()
    if state is not None:
        cached = state.get_meta('_server_meta')
        if cached is not None:
            return cached  # type: ignore[return-value]
    meta: dict[str, object] = {'server_version': current_version()}
    latest = _latest_local_cache() or _latest_network()
    if _is_newer(latest, current_version()):
        meta['update'] = {
            'available': True,
            'latest': latest,
            'message': 'Доступна новая версия onec-converter: '
                       f'{latest} (pip install --upgrade onec-converter)'}
    if state is not None:
        state.set_meta('_server_meta', meta)
    return meta


def _latest_local_cache() -> str | None:
    from .version_check import _VERSION_CACHE

    try:
        saved = json.loads(_VERSION_CACHE.read_text(encoding='utf-8'))
        return (saved.get('latest') or '') or None
    except (OSError, ValueError):
        return None


def _latest_network() -> str | None:
    try:
        from .version_check import latest_version

        return latest_version()
    except Exception:  # noqa: BLE001 — проверка не должна ронять тул
        return None


def visible_tool(name: str, description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор тула: логирует применение команды в терминал (stderr)
    и регистрирует тул в FastMCP. Ответ дополняется полем `next`
    (рекомендуемая следующая команда плейбука), если тул вернул JSON-объект.
    """

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = now_ms()
            arg_parts = [str(a) for a in args[:2]]
            arg_parts += [f'{k}={v}' for k, v in list(kwargs.items())[:3]]
            args_repr = ', '.join(arg_parts)
            tool_started(name, args_repr)
            try:
                result = fn(*args, **kwargs)
                summary = tool_summary(result)
                tool_finished(name, True, now_ms() - started, summary)
                if isinstance(result, str):
                    try:
                        data = json.loads(result)
                        if isinstance(data, dict):
                            data.setdefault('next', PLAYBOOK_NEXT.get(name, ''))
                            data.setdefault('server_version',
                                            _server_meta()['server_version'])
                            upd = _server_meta().get('update')
                            if isinstance(upd, dict) and upd.get('available'):
                                data.setdefault('update', upd)
                            return json.dumps(data, ensure_ascii=False)
                    except (ValueError, TypeError):
                        pass
                return result
            except Exception as exc:
                tool_error(name, now_ms() - started, str(exc))
                raise

        mcp.add_tool(wrapper, name=name, description=description)
        return wrapper

    return deco


# Рекомендуемая следующая команда для каждого тула (плейбук).
PLAYBOOK_NEXT: dict[str, str] = {
    'tools': 'pipeline_status()',
    'pipeline_status': "search_schema(source_dir, 'Зарплат') — найти объекты переноса",
    'search_schema': 'table_sizes(source_dir, "Reference") — оценить объём',
    'table_sizes': 'compare_structures(source_dir, target_dir) — расхождения структур',
    'base_health': 'compare_structures(source_dir, target_dir) — расхождения структур',
    'compare_structures': 'auto_map_schemas(source_dir, target_dir) — автогенерация TOON-правил',
    'auto_map_schemas': "migrate(project_dir, source_ib_id, target_ib_id, source_dir, "
                        "target_url, rules) — сквозной перенос",
    'explain_diff': 'auto_map_schemas(source_dir, target_dir) — автогенерация правил маппинга',
    'dump_metadata': 'compare_structures(source_dir, target_dir)',
    'compress_metadata': 'auto_map_schemas(source_dir, target_dir)',
    'config_versions': 'table_sizes(source_dir, "") — объём таблиц',
    'query_sql': 'migrate(project_dir, source_ib_id, target_ib_id, source_dir, '
                 "target_url, rules) — сквозной перенос данных",
    'migrate': 'guid_diff(source_dir, target_dir) — сверка полноты по GUID',
    'load_direct': 'guid_diff(source_dir, target_dir) — сверка полноты по GUID',
    'guid_diff': 'pipeline_status()',
    'audit_verify': 'guid_diff(source_dir, target_dir) — сверка полноты по GUID',
    'cache_stats': 'pipeline_status()',
    'playbook': 'tools()',
}


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
                  source_dir: str, source_encoding: str = 'cp866') -> dict[str, Any]:
        """
        source_encoding — кодировка .dat 7.7 (A4): 'cp866' (по умолчанию)
        или 'cp1251'; строки перекодируются в UTF-8 в промежуточном формате.
        """
        self.project_dir = Path(project_dir)
        self.binding = ProjectBinding.create(self.project_dir, source_ib_id, target_ib_id)
        self.source = Base77(Path(source_dir), encoding=source_encoding)
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

    def step_extract(self, out_file: str, stream: bool = False,
                     objects: str = '') -> dict[str, Any]:
        """Извлечение данных в intermediate JSON.

        objects — селективный перенос (Фаза 29.2): CSV спецификаций
        "Раздел.Имя" или группы "Раздел.*"; пусто — все данные.
        """
        if self.source is None:
            raise ValueError('вызовите init')
        reader = self.source.data
        from collections.abc import Iterable as _Iter

        from .intermediate import save_json_stream
        from .objects_filter import ObjectSpec, parse_objects, selects

        specs: list[ObjectSpec] = parse_objects(
            [o.strip() for o in objects.split(',')]) if objects else []

        def _gen() -> _Iter[dict[str, Any]]:
            for table_id, recs in reader.references().items():
                if specs and not selects(specs, 'Справочник', str(table_id)):
                    continue
                for rec in recs:
                    if not rec:
                        continue
                    yield {
                        OBJ_TYPE: f'Справочник.{table_id}',
                        'id': str(rec[0]),
                        'key': [str(v) for v in rec[1:3]],
                        'attributes': {'_code': rec[1] if len(rec) > 1 else None,
                                       '_descr': rec[2] if len(rec) > 2 else None},
                        'references': {},
                    }

        if stream:
            # потоковая запись без накопления всех объектов в памяти (Фаза 20)
            save_json_stream(_gen(), out_file)
            self.extracted = []  # для больших баз не держим в памяти
            self._mark('extract')
            get_audit().info('extract', obj='stream', result='ok',
                             detail=out_file)
            return {'ok': True, 'objects': 'stream',
                    'file': out_file, 'stream': True}
        objs = list(_gen())
        self.extracted = objs
        self._mark('extract')
        save_json_batch(objs, out_file)
        for o in objs:
            get_audit().info('extract', obj=str(o.get(OBJ_TYPE, '')),
                             guid=str(o.get('id', '')), result='ok')
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
        steps = [{'name': 'init', 'doc': 'Привязка пары источник→приёмник (правило 1→1)'},
                {'name': 'inspect_source', 'doc': 'Метаданные источника (из кеша или парсинга)'},
                {'name': 'extract', 'doc': 'Данные источника -> промежуточный JSON'},
                {'name': 'inspect_target', 'doc': 'Структура приёмника'},
                {'name': 'map', 'doc': 'Правила маппинга (LLM/JSON)'},
                {'name': 'transform', 'doc': 'Применение правил'},
                {'name': 'prevalidate', 'doc': 'Контроль количества/ссылок/дубликатов'},
                {'name': 'preview', 'doc': 'Пробная загрузка (dry-run)'},
                {'name': 'load', 'doc': 'Запись в приёмник через HTTP-сервис'},
                {'name': 'verify', 'doc': 'Сверка источник↔приёмник (полнота переноса)'}]
        if _current_role() == 'inspect':
            # U23: role=inspect — только чтение; write-шаги скрыты из списка
            write = {'init', 'extract', 'map', 'transform', 'load', 'preview'}
            steps = [s for s in steps if s['name'] not in write]
        return steps


@visible_tool('pipeline_status', 'Состояние пайплайна переноса: коннекторы, кеш, последний шаг, метрики (точка входа для LLM)')
def pipeline_status() -> str:
    """Статус пайплайна переноса: коннекторы, кеш, последний шаг, метрики (точка входа для LLM)."""
    state = PipelineState(Path('.'))
    st = state.step_status()
    st['timings'] = GLOBAL_TIMINGS.snapshot()
    return json.dumps(st, ensure_ascii=False)


@visible_tool('tools', 'Список тулов пайплайна (точка входа для LLM-агента)')
def tools() -> list[dict[str, Any]]:
    """Список тулов пайплайна (точка входа для LLM-агента)."""
    return PipelineState(Path('.')).tools()


@visible_tool('base_health', 'Здоровье базы 1CD: версия, таблицы/строки, блокировки, свободное место (Фаза 27, идея OneS2Zabbix)')
def base_health(source_dir: str, include_rows: bool = False) -> str:
    """Сводка «здоровья» файловой ИБ 8.x для мониторинга/агента.

    source_dir — каталог с 1Cv8.1CD (read-only); include_rows — помимо
    быстрого health-пинга посчитать число строк (читает данные таблиц,
    может быть долгим на больших базах). Возвращает JSON: version
    (формат), tables, rows, rows_computed, locks (1Cv8.1CL/1Cv8tmp*),
    free_bytes, file_bytes.
    """
    from .health import HealthError
    from .health import base_health as _health

    try:
        rep = _health(source_dir, include_rows=include_rows)
    except HealthError as exc:
        return json.dumps({'ok': False, 'error': str(exc)},
                          ensure_ascii=False)
    return json.dumps(rep, ensure_ascii=False, default=str)


@visible_tool('table_sizes', 'Размеры таблиц базы 1CD: JSON или XLSX-отчёт (идея A2: метрики 1C_PrometheusExporter)')
def table_sizes(source_dir: str, tables: str = '', format: str = 'json',
                out_file: str = '', top_n: int = 50) -> str:
    """Размеры таблиц базы 1CD (идея A2: метрики 1C_PrometheusExporter).

    source_dir — каталог с 1Cv8.1CD; tables — подстрока фильтра по имени
    (пусто = все таблицы); format — 'json' (по умолчанию) или 'xlsx'
    (отчёт в out_file). JSON: {name: {rows, bytes}} — число строк
    и объём данных каждой таблицы для оценки объёма переноса.
    """
    from .source_8x_file import Database1CD

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False,
                           'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    with Database1CD(cd) as db:
        names = sorted(db.tables)
        if tables:
            names = [n for n in names if tables.lower() in n.lower()]
        out = {n: dict(zip(('rows', 'bytes'), db.table_stats(n)))
               for n in names}
    if format == 'xlsx':
        if not out_file:
            return json.dumps({'ok': False,
                               'error': 'xlsx: укажите out_file'},
                              ensure_ascii=False)
        from .xlsx_report import build_sizes_report
        sizes = [(n, out[n]['rows'], out[n]['bytes']) for n in names]
        outp = Path(out_file)
        outp.parent.mkdir(parents=True, exist_ok=True)
        build_sizes_report(sizes, outp, top_n=top_n)
        return json.dumps({'ok': True, 'path': str(outp),
                           'tables': len(sizes)}, ensure_ascii=False)
    return json.dumps({'ok': True, 'count': len(out), 'tables': out},
                      ensure_ascii=False)


@visible_tool('compare_structures', 'Diff-отчёт структур двух баз 1CD: JSON или XLSX (идея C2: RDT1C)')
def compare_structures(source_dir: str, target_dir: str, format: str = 'json',
                       out_file: str = '') -> str:
    """Diff-отчёт структур двух баз 1CD (идея C2: RDT1C анализ конфигураций).

    Объекты только в источнике / только в приёмнике / общие (с совпадением
    типов полей). format — 'json' (по умолчанию) или 'xlsx' (листы «Только
    в источнике»/«Только в приёмнике»/«Расхождения типов», нужен out_file).
    """
    from .source_8x_file import read_metadata

    src = Path(source_dir) / '1Cv8.1CD'
    tgt = Path(target_dir) / '1Cv8.1CD'
    if not src.is_file() or not tgt.is_file():
        return json.dumps({'ok': False, 'error': 'нет 1Cv8.1CD в source_dir/target_dir'},
                          ensure_ascii=False)
    ms = _run_timeout(60, read_metadata, src)
    mt = _run_timeout(60, read_metadata, tgt)
    d = diff_structures(ms, mt)
    if format == 'xlsx':
        if not out_file:
            return json.dumps({'ok': False,
                               'error': 'xlsx: укажите out_file'},
                              ensure_ascii=False)
        from .xlsx_report import build_structure_report
        outp = Path(out_file)
        outp.parent.mkdir(parents=True, exist_ok=True)
        build_structure_report(d, outp)
        return json.dumps({'ok': True, 'path': str(outp), 'counts': d['counts']},
                          ensure_ascii=False)
    return json.dumps({'ok': True,
                       'only_source': d['only_source'][:100],
                       'only_target': d['only_target'][:100],
                       'type_mismatch': d['type_mismatch'][:100],
                       'counts': d['counts']},
                      ensure_ascii=False)


@visible_tool('auto_map_schemas', 'Авто-маппинг полей между двумя базами по именам/синонимам (Фаза 40)')
def auto_map_schemas(source_dir: str, target_dir: str) -> str:
    """Предложить правила TOON (rules.json) по нормализованному имени.

    Сопоставляет объекты по kind+имени/синониму, реквизиты — по имени
    (нормализованному). Возвращает {ok, rules, matched, unmatched} — готовую
    основу для map, LLM лишь редактирует исключения.
    """
    from .ai_skills import auto_map_schemas as _amap
    from .source_8x_file import read_metadata

    src = Path(source_dir) / '1Cv8.1CD'
    tgt = Path(target_dir) / '1Cv8.1CD'
    if not src.is_file() or not tgt.is_file():
        return json.dumps({'ok': False,
                           'error': 'нет 1Cv8.1CD в source_dir/target_dir'},
                          ensure_ascii=False)
    try:
        res = _amap(_run_timeout(60, read_metadata, src),
                     _run_timeout(60, read_metadata, tgt))
    except Exception as exc:  # noqa: BLE001 — вернуть ошибку как JSON
        return json.dumps({'ok': False, 'error': str(exc)},
                          ensure_ascii=False)
    return json.dumps(res, ensure_ascii=False)


@visible_tool('explain_diff', 'Объяснение причин расхождений структур двух баз (Фаза 40)')
def explain_diff(source_dir: str, target_dir: str) -> str:
    """Человекочитаемые причины расхождений (а не сухие списки diff)."""
    from .ai_skills import explain_diff as _explain
    from .source_8x_file import read_metadata

    src = Path(source_dir) / '1Cv8.1CD'
    tgt = Path(target_dir) / '1Cv8.1CD'
    if not src.is_file() or not tgt.is_file():
        return json.dumps({'ok': False,
                           'error': 'нет 1Cv8.1CD в source_dir/target_dir'},
                          ensure_ascii=False)
    md = diff_structures(_run_timeout(60, read_metadata, src),
                          _run_timeout(60, read_metadata, tgt))
    reasons = _explain(md)
    return json.dumps({'ok': True, 'explanations': reasons[:50]},
                      ensure_ascii=False)


@visible_tool('search_schema', 'Двунаправленный поиск метаданные↔таблицы (идея C1: 1CDBStorageStructureInfo)')
def search_schema(source_dir: str, query: str) -> str:
    """Двунаправленный поиск метаданные↔таблицы (идея C1: 1CDBStorageStructureInfo).

    Ищет по имени/синониму объекта («Номенклатура»), по имени таблицы
    («REFERENCE106»/_Reference74) и по именам полей. Возвращает совпадения
    с типами и привязкой к таблице.
    """
    from .source_8x_file import read_metadata

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False, 'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    md = _run_timeout(60, read_metadata, cd)
    q = query.strip().lower()
    hits = []
    for o in md['objects']:
        name = o['name'] or ''
        syn = o.get('synonym') or ''
        table = o['table'] or ''
        if q in name.lower() or q in syn.lower() or q in table.lower():
            hits.append({'kind': o['kind'], 'name': name, 'synonym': syn,
                         'table': table, 'ref_num': o['ref_num']})
    # поиск по именам физических полей (FldNNN/системные)
    fields = []
    if not hits:
        for o in md['objects']:
            for a in o['attributes']:
                if q in a['name'].lower() or q in (a['field'] or '').lower():
                    fields.append({'object': f"{o['kind']}.{o['name']}",
                                   'field': a['field'], 'attr': a['name'],
                                   'type': a['type']})
    return json.dumps({'ok': True, 'query': query,
                       'objects': hits[:50], 'fields': fields[:50]},
                      ensure_ascii=False)


def diff_structures(ms: dict[str, Any], mt: dict[str, Any]) -> dict[str, Any]:
    """Diff двух метаданных (структура): only_source/only_target/type_mismatch.

    Чистая функция — используется JSON-тулом compare_structures и XLSX-тулом
    structure_report (Фаза 8), чтобы оба отчёта строились из одних данных.
    """
    def key(o: dict[str, Any]) -> str:
        return f"{o['kind']}.{o['name']}"

    by_src = {key(o): o for o in ms['objects']}
    by_tgt = {key(o): o for o in mt['objects']}
    only_src = [k for k in by_src if k not in by_tgt]
    only_tgt = [k for k in by_tgt if k not in by_src]
    diff_types = []
    for k in set(by_src) & set(by_tgt):
        sa = {a['name']: a['type'] for a in by_src[k]['attributes']}
        ta = {a['name']: a['type'] for a in by_tgt[k]['attributes']}
        for attr in set(sa) & set(ta):
            if sa[attr] != ta[attr]:
                diff_types.append({'object': k, 'attr': attr,
                                   'source_type': sa[attr], 'target_type': ta[attr]})
    return {'only_source': sorted(only_src),
            'only_target': sorted(only_tgt),
            'type_mismatch': diff_types,
            'counts': {'only_source': len(only_src),
                       'only_target': len(only_tgt),
                       'mismatch': len(diff_types)}}


@visible_tool('query_sql', 'Консоль запросов конфигурации: SQL-подобная выборка (Фаза 11, E1)')
def query_sql(source_dir: str, table: str, select: str = '*', where: str = '',
              order_by: str = '', limit: int = 100) -> str:
    """SQL-подобная выборка записей таблицы 1CD (идея E1).

    SELECT — `*` или поля через запятую; WHERE — `f=1; g>10; name LIKE 'A%'`;
    ORDER BY — `поле ASC|DESC`; LIMIT — число. REF-поля → {guid, name}.
    Синтаксис WHERE совместим с query_table (C3).
    """
    from .query import QueryError, query_table_sql
    from .source_8x_file import Database1CD

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False, 'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    try:
        with Database1CD(cd) as db:
            rows = query_table_sql(db, table, select=select, where=where,
                                   order_by=order_by, limit=limit)
    except QueryError as exc:
        return json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False)
    return json.dumps({'ok': True, 'table': table, 'count': len(rows),
                       'rows': rows}, ensure_ascii=False, default=str)


@visible_tool('guid_diff', 'Сверка двух баз по GUID: объекты и таблицы (Фаза 11, E2)')
def guid_diff(source_dir: str, target_dir: str) -> str:
    """Проверка полноты переноса по стабильным GUID (идея E2).

    Объекты конфигурации (read_metadata) и таблицы (read_dbnames):
    только-в-источнике / только-в-приёмнике / общие с расхождениями
    имени или типа. `full` — перенос структуры завершён.
    """
    from .guid_diff import guid_diff as _guid_diff

    try:
        report = _guid_diff(source_dir, target_dir)
    except (OSError, ValueError) as exc:
        return json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False)
    return json.dumps(report, ensure_ascii=False, default=str)


@visible_tool('config_versions', 'Версии конфигурации из файла базы: формат, ИБ/платформа, дифф CONFIG↔CONFIGSAVE (Фаза 11, E3)')
def config_versions(source_dir: str) -> str:
    """Версии и сохранения конфигурации (идея E3).

    Формат файла, версия ИБ и требуемая платформа (IBVERSION), статистика
    файлов CONFIG/CONFIGSAVE/PARAMS, дифф CONFIG↔CONFIGSAVE — «что
    изменилось с последнего сохранения».
    """
    from .config_versions import config_versions as _config_versions

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False, 'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    try:
        report = _config_versions(cd)
    except (OSError, ValueError) as exc:
        return json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False)
    return json.dumps(report, ensure_ascii=False, default=str)


@visible_tool('load_direct', 'Прямая загрузка в 1CD без HTTP-расширения: объекты → копия 1Cv8.1CD приёмника (Фаза 13, zero-setup A)')
def load_direct(target_dir: str, input_file: str, workdir: str = '',
                no_snapshot: bool = False) -> str:
    """Прямая запись объектов (батч после transform) в КОПИЮ приёмника.

    Оригинал не изменяется; копия создаётся в workdir (или temp). До записи
    сохраняется workdir/snapshot.1CD (откат при сбое, Фаза 24);
    no_snapshot=true отключает. Возвращает {ok, copy_path, total, tables,
    snapshot}. Роль клиента (RBAC, Фаза 37): требует ONEC_MCP_ROLE=load
    (запись). Ограничения MVP — docs/zero-setup.md.
    """
    _require_role('load', 'load_direct')
    from .intermediate import load_json_batch
    from .load_8x import LoadError
    from .load_8x import load_direct as _load_direct

    p = Path(input_file)
    if not p.is_file():
        return json.dumps({'ok': False, 'error': f'нет файла батча: {input_file}'},
                          ensure_ascii=False)
    objs = load_json_batch(p)
    try:
        rep = _load_direct(target_dir, objs, workdir or None,
                           snapshot=not no_snapshot)
    except LoadError as exc:
        return json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False)
    return json.dumps(rep, ensure_ascii=False, default=str)


@visible_tool('dump_metadata', 'Дамп метаданных базы в git-дружественный текст (идея D1: GitConverter)')
def dump_metadata(source_dir: str, out_file: str = '', fmt: str = 'json') -> str:
    """Дамп метаданных базы в git-дружественный текст (идея D1: GitConverter).

    Структура (объекты, типы, привязка таблиц, поля) записывается в JSON
    или YAML — файл удобен для ревью изменений конфигурации в git.
    out_file: путь результата (пусто — только вернуть в ответе).
    """
    from .source_8x_file import read_metadata

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False, 'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    md = read_metadata(cd)
    payload = {'source_dir': str(cd), 'objects': md['objects'],
               'total': len(md['objects'])}
    if fmt == 'yaml':
        import yaml  # type: ignore[import-untyped]

        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    written = ''
    if out_file:
        p = Path(out_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        written = str(p)
    return json.dumps({'ok': True, 'fmt': fmt, 'objects': len(md['objects']),
                       'out_file': written, 'text': text[:2000]},
                      ensure_ascii=False)


@visible_tool('playbook', 'Универсальная последовательность команд переноса данных (см. docs/playbook.md)')
def playbook() -> str:
    """Возвращает универсальную последовательность команд MCP-сервера
    (плейбук) для переноса данных между ИБ 1С. Ответ каждого тула содержит
    поле `next` — следующую рекомендуемую команду, поэтому агент движется
    по плейбуку автоматически. Для конкретного примера (начисления
    заработной платы 8.1→8.3) — см. docs/playbook.md.
    """
    return json.dumps({'ok': True, 'steps': PLAYBOOK,
                       'sequence': _playbook_summary(),
                       'next': PLAYBOOK_NEXT.get('playbook', 'tools()')},
                      ensure_ascii=False)


@visible_tool('migrate', 'Сквозной перенос 7.7→8.3 (Фаза 7): init → inspect → extract → map → transform → validate → load')
def migrate(project_dir: str, source_ib_id: str, target_ib_id: str,
            source_dir: str, target_url: str, rules: str = '{}',
            out_file: str = '', source_encoding: str = 'cp866') -> str:
    """Полный сценарий переноса данных 7.7 в приёмник 8.3 одной командой.

    Выполняет шаги пайплайна последовательно (каждый логируется в терминал):
      init → inspect_source → extract → map (валидация правил) →
      transform (применение правил) → prevalidate → load (HTTP /load).
    `rules` — JSON TOON-правил (см. step_map); `target_url` — HTTP-сервис
    приёмника 8.3; `out_file` — промежуточный JSON (пусто = временный).
    Реальные базы не изменяются: запись только через HTTP-сервис приёмника.
    Write-тул: при ONEC_MCP_ROLE=inspect недоступен (U23).
    """
    from .terminal import playbook_step
    from .transform import transform_object

    _require_role('load', 'migrate')
    steps: list[dict[str, Any]] = []

    def log(name: str, ok: bool, ms: float, summary: str) -> None:
        steps.append({'name': name, 'ok': ok, 'ms': round(ms, 1), 'summary': summary})

    st = PipelineState(Path(project_dir))
    try:
        playbook_step(1, 7, 'init')
        t0 = now_ms()
        r = st.step_init(project_dir, source_ib_id, target_ib_id,
                         source_dir, source_encoding=source_encoding)
        log('init', bool(r.get('ok')), now_ms() - t0, str(r.get('binding')))

        playbook_step(2, 7, 'inspect_source')
        t0 = now_ms()
        r = st.step_inspect_source()
        meta_source = r['metadata']
        log('inspect_source', bool(r.get('ok')), now_ms() - t0,
            f"references={meta_source.get('references_tables')}")

        playbook_step(3, 7, 'extract')
        t0 = now_ms()
        out = out_file or str(Path(project_dir) / 'intermediate.json')
        r = st.step_extract(out)
        log('extract', bool(r.get('ok')), now_ms() - t0, f"objects={r.get('objects')}")

        playbook_step(4, 7, 'map (правила TOON)')
        t0 = now_ms()
        parsed_rules: dict[str, Any] = json.loads(rules) if rules.strip() else {}
        r = st.step_map(meta_source, {}, parsed_rules)
        log('map', bool(r.get('ok')), now_ms() - t0,
            'ok' if r.get('ok') else f"errors={r.get('errors')}")
        if not r.get('ok'):
            raise ValueError(f'правила маппинга невалидны: {r.get("errors")}')

        playbook_step(5, 7, 'transform')
        t0 = now_ms()
        from .resolver import RefResolver
        resolver = RefResolver()
        transformed: list[dict[str, Any]] = []
        for obj in st.extracted:
            for rule in parsed_rules.get('objects', []):
                if rule.get('source') == obj.get('type'):
                    transformed.append(transform_object(obj, rule, resolver))
                    break
        log('transform', True, now_ms() - t0, f"objects={len(transformed)}")

        playbook_step(6, 7, 'prevalidate')
        t0 = now_ms()
        vr = validate_batch(transformed)
        log('prevalidate', vr.ok, now_ms() - t0,
            f"counts={vr.counts}, errors={len(vr.errors)}")
        if not vr.ok:
            raise ValueError(f'предвалидация не прошла: {vr.errors[:5]}')

        playbook_step(7, 7, 'load')
        t0 = now_ms()
        try:
            created = _http_load(transformed, source_ib_id, target_ib_id, target_url)
            log('load', True, now_ms() - t0, f"created={created}")
        except Exception as exc:
            log('load', False, now_ms() - t0, str(exc))
            raise

        st._mark('migrate')
        return json.dumps({'ok': True, 'created': created,
                           'objects': len(transformed), 'steps': steps,
                           'next': 'verify — сверка источник↔приёмник (полнота переноса)'},
                          ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 — MCP-тул возвращает ошибку строкой
        return json.dumps({'ok': False, 'error': str(exc), 'steps': steps},
                          ensure_ascii=False)


@visible_tool('compress_metadata', 'Сжатие метаданных базы 1CD до краткого саммари для LLM (kinds, top-таблицы, объём атрибутов) — экономия токенов (U19)')
def _mcp_compress_metadata(source_dir: str, top_tables: int = 15) -> str:
    """Сжать метаданные базы 1CD до саммари для LLM. Обычно передать весь
    read_metadata (тысячи объектов) агенту — дорого; саммари дешевле.
    """
    from .ai_skills import compress_metadata
    from .source_8x_file import read_metadata

    md = _run_timeout(60, read_metadata, source_dir)
    summary = compress_metadata(md, top_tables=top_tables)
    return json.dumps(summary, ensure_ascii=False)


@visible_tool('audit_verify', 'Проверка целостности audit-журнала (tamper-evident chain) — хеш-цепочка и границы ротации (U20)')
def _mcp_audit_verify(audit_file: str, cross_files: bool = False) -> str:
    """Проверить tamper-evident цепочку audit-журнала; empty-нарушений = ок.
    """
    from .audit import verify_audit

    errs = _run_timeout(30, verify_audit, audit_file, cross_files)
    return json.dumps({'ok': len(errs) == 0, 'errors': errs[:50],
                       'count': len(errs)}, ensure_ascii=False)


@visible_tool('cache_stats', 'Метрики дискового кеша: файлы, байты, самый старый артефакт (U22)')
def _mcp_cache_stats(root_dir: str = '') -> str:
    """Статистика кеша onec (файлы, размер, возраст), может задать root_dir.
    """
    from .cache import Cache
    from .source_8x_file import _metadata_disk_cache

    cache = Cache(root=Path(root_dir)) if root_dir else _metadata_disk_cache()
    stats = cache.stats()
    return json.dumps({'ok': True, **stats}, ensure_ascii=False)


def _run_timeout(seconds: float, fn: Callable[..., Any], *args: Any,
                 **kwargs: Any) -> Any:
    """Выполнить блокирующий вызов с твёрдым таймаутом (U21).

    future.result(timeout) поднимает TimeoutError по истечении времени, не
    дожидаясь завершения фонового потока (asyncio.run ждёл join экзекьютора
    — не подходит). Возвращает результат либо бросает TimeoutError; поток
    умирает сам после работы.
    """
    import concurrent.futures

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=seconds)
    except concurrent.futures.TimeoutError as exc:
        raise TimeoutError(f'MCP-тул превысил таймаут {seconds}s') from exc


def _http_load(objects: list[dict[str, Any]], source_ib: str, target_ib: str,
               target_url: str) -> int:
    """Загрузка через HTTP-сервис приёмника (async внутри sync-тула)."""
    from .http_client import HttpClient83

    async def run() -> int:
        client = HttpClient83(target_url)
        try:
            results = await client.load(objects, source_ib, target_ib)
        finally:
            await client.aclose()
        return sum(r.created for r in results)

    return asyncio.run(run())


def server_main(transport: str = 'stdio') -> None:
    """Запуск MCP-сервера (stdio по умолчанию). CLI: onec-converter mcp --stdio.

    Аудит раунда 6 (C1/U15): раньше `python -m onec_converter.mcp_server`
    только импортировал модуль и завершался — сервер не запускался.
    Теперь точка входа run() держит stdio-транспорт для MCP-клиентов
    (Claude/Cursor/pi), stdout занят JSON-RPC, события — в stderr.
    При старте в stderr печатается версия релиза и (если есть) уведомление
    о доступной новой версии на PyPI (см. version_check).
    """
    import logging as _logging

    # MCP SDK логирует INFO-сообщения ('Processing request…') в stderr, что
    # мешает читать баннер версии; снижаем громкость до WARNING (пи/Claude
    # читают stderr процесса как диагностику).
    for _lg in ('mcp', 'mcp.server.server', 'mcp.server.session'):
        _logger = _logging.getLogger(_lg)
        if _logger.level < _logging.WARNING:
            _logger.setLevel(_logging.WARNING)
    try:
        from .version_check import print_version_to_stderr

        print_version_to_stderr()
        mcp.run(transport=transport)  # type: ignore[arg-type]
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    server_main()
