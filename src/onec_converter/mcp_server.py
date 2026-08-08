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

import functools
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
from .source_8x_file import decode_field
from .terminal import now_ms, tool_error, tool_finished, tool_started, tool_summary
from .timings import GLOBAL as GLOBAL_TIMINGS
from .validate import validate_batch

mcp = FastMCP('onec-converter')

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
    {'step': '4', 'command': "table_sizes(source_dir, '<фильтр>')",
     'goal': 'Оценить объём: строки и байты по таблицам (что переносить)'},
    {'step': '5', 'command': 'compare_structures(source_dir, target_dir)',
     'goal': 'Расхождения структур: только в источнике/приёмнике, разные типы'},
    {'step': '6',
     'command': 'step_init(project_dir, source_ib_id, target_ib_id, '
                "source_dir, source_encoding='cp866')",
     'goal': 'Привязка пары источник→приёмник (правило 1→1)'},
    {'step': '7', 'command': 'step_inspect_source()',
     'goal': 'Метаданные источника (справочники, документы, секции)'},
    {'step': '8', 'command': 'step_inspect_target(target_metadata)',
     'goal': 'Структура приёмника (через HTTP-расширение 8.3)'},
    {'step': '9', 'command': 'step_map(meta_source, meta_target, rules)',
     'goal': 'Валидация TOON-правил маппинга + промпт для LLM'},
    {'step': '10', 'command': 'query_table(source_dir, table, filters, limit)',
     'goal': 'Выборочная проверка данных (пример записи, контроль условий)'},
    {'step': '11', 'command': 'step_extract(out_file)',
     'goal': 'Извлечение данных источника в промежуточный JSON'},
    {'step': '12', 'command': 'step_prevalidate()',
     'goal': 'Контроль количества, ссылок, дубликатов перед загрузкой'},
    {'step': '13', 'command': 'transform → preview',
     'goal': 'Применение правил маппинга, пробная загрузка (dry-run)'},
    {'step': '14', 'command': 'step_load(http_load)',
     'goal': 'Запись в приёмник через HTTP-сервис (с ретраями)'},
    {'step': '15', 'command': 'verify',
     'goal': 'Сверка источник↔приёмник: полнота переноса, контроль'},
    {'step': '16', 'command': 'pipeline_status()',
     'goal': 'Итоговое состояние пайплайна + метрики времени'},
]


def _playbook_summary() -> str:
    return ' → '.join(p['command'].split('(')[0] for p in PLAYBOOK)


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
    'compare_structures': 'step_init(project_dir, source_ib_id, target_ib_id, '
                          "source_dir, source_encoding='cp866')",
    'dump_metadata': 'compare_structures(source_dir, target_dir)',
    'query_table': 'step_extract(out_file) — извлечение данных в intermediate JSON',
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


@visible_tool('table_sizes', 'Размеры таблиц базы 1CD (идея A2: метрики 1C_PrometheusExporter)')
def table_sizes(source_dir: str, tables: str = '') -> str:
    """Размеры таблиц базы 1CD (идея A2: метрики 1C_PrometheusExporter).

    source_dir — каталог с 1Cv8.1CD; tables — подстрока фильтра по имени
    (пусто = все таблицы). Возвращает {name: {rows, bytes}} — число строк
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
    return json.dumps({'ok': True, 'count': len(out), 'tables': out},
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
    md = read_metadata(cd)
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


@visible_tool('compare_structures', 'Diff-отчёт структур двух баз 1CD (идея C2: RDT1C)')
def compare_structures(source_dir: str, target_dir: str) -> str:
    """Diff-отчёт структур двух баз 1CD (идея C2: RDT1C анализ конфигураций).

    Объекты только в источнике / только в приёмнике / общие (с совпадением
    типов полей). Полезен для плана конвертации перед переносом.
    """
    from .source_8x_file import read_metadata

    src = Path(source_dir) / '1Cv8.1CD'
    tgt = Path(target_dir) / '1Cv8.1CD'
    if not src.is_file() or not tgt.is_file():
        return json.dumps({'ok': False, 'error': 'нет 1Cv8.1CD в source_dir/target_dir'},
                          ensure_ascii=False)
    ms = read_metadata(src)
    mt = read_metadata(tgt)

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
    return json.dumps({'ok': True,
                       'only_source': sorted(only_src)[:100],
                       'only_target': sorted(only_tgt)[:100],
                       'type_mismatch': diff_types[:100],
                       'counts': {'only_source': len(only_src),
                                  'only_target': len(only_tgt),
                                  'mismatch': len(diff_types)}},
                      ensure_ascii=False)


@visible_tool('query_table', 'Консоль запросов: выборка записей таблицы 1CD с фильтрами (идея C3)')
def query_table(source_dir: str, table: str, filters: str = '',
                limit: int = 100) -> str:
    """Консоль запросов: выборка записей таблицы 1CD с фильтрами (идея C3).

    filters — строка вида "Поле1=знач1; Поле2>10" (операторы =, !=, >, <, >=, <=;
    сравнение строк — точное, чисел/дат — по значению). Возвращает до limit
    записей (по умолчанию 100).
    """
    from .source_8x_file import Database1CD

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return json.dumps({'ok': False, 'error': f'нет 1Cv8.1CD в {source_dir}'},
                          ensure_ascii=False)
    conds: list[tuple[str, str, Any]] = []
    for part in [p for p in filters.split(';') if p.strip()]:
        for op in ('>=', '<=', '!=', '=', '>', '<'):
            if op in part:
                fname, _, raw = part.partition(op)
                conds.append((fname.strip(), op, raw.strip()))
                break
    with Database1CD(cd) as db:
        if table not in db.tables:
            return json.dumps({'ok': False, 'error': f'таблица не найдена: {table}'},
                              ensure_ascii=False)
        t = db.tables[table]
        out = []
        for row in db.table_rows(t):
            rec = {fn: decode_field(fd, row[fd.offset:fd.offset + fd.size])
                   for fn, fd in t.fields.items()}
            ok = True
            for fname, op, expected in conds:
                if fname not in rec:
                    ok = False
                    break
                val = rec[fname]
                try:
                    exp_num = float(expected)
                    val_num = float(val)
                    cmp: tuple[Any, Any] = (val_num, exp_num)
                except (ValueError, TypeError):
                    cmp = (str(val), expected)
                if op == '=' and cmp[0] != cmp[1] or op == '!=' and cmp[0] == cmp[1] or op == '>' and not cmp[0] > cmp[1] or op == '<' and not cmp[0] < cmp[1] or op == '>=' and not cmp[0] >= cmp[1] or op == '<=' and not cmp[0] <= cmp[1]:
                    ok = False
                if not ok:
                    break
            if ok:
                out.append(rec)
                if len(out) >= limit:
                    break
    return json.dumps({'ok': True, 'table': table, 'filters': filters,
                       'count': len(out), 'rows': out}, ensure_ascii=False,
                      default=str)


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
