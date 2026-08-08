"""CLI-обёртка пайплайна onec_converter (без MCP-клиента).

Команды в терминале: inspect, extract, map, transform, load, status.
Только stdlib (argparse); переиспользует модули пайплайна, не дублируя логику.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .http_client import HttpClient83
from .intermediate import (
    OBJ_ATTRS,
    OBJ_ID,
    OBJ_KEY,
    OBJ_REFS,
    OBJ_TYPE,
    load_json_batch,
    save_json_batch,
)
from .mapping import MappingError, build_prompt, load_rules
from .query import QueryError
from .resolver import RefResolver
from .transform import TransformError, transform_object
from .validate import validate_batch


class CLIError(Exception):
    """Ошибка CLI: сообщение в stderr, код возврата 1."""


def _err(msg: str) -> int:
    print(f'onec-converter: {msg}', file=sys.stderr)
    return 1


def _detect_version(source_dir: str) -> str:
    """Версия источника по файлам: '77' | '8x'."""
    d = Path(source_dir)
    if (d / '1Cv8.1CD').is_file():
        return '8x'
    if (d / '1Cv7.MD').is_file() and (d / '1Cv77.dat').is_file():
        return '77'
    raise CLIError(f'источник не найден: {source_dir} (нет 1Cv8.1CD или 1Cv7.MD/1Cv77.dat)')


# ---- inspect ----

def cmd_inspect(args: argparse.Namespace) -> int:
    """Метаданные источника: объекты/виды (7.7) или таблицы+размеры (8.x)."""
    from .base_reader import Base77
    from .source_8x_file import Database1CD

    ver = _detect_version(args.source_dir)
    if ver == '77':
        base = Base77(Path(args.source_dir), encoding=args.source_encoding)
        reader = base.data
        meta: dict[str, Any] = {
            'version': '7.7',
            'sections': reader.sections(),
            'unique_ids': reader.unique_ids(),
            'constants': len(reader.constants()),
            'references_tables': len(reader.references()),
        }
    else:
        cd = Path(args.source_dir) / '1Cv8.1CD'
        tables: dict[str, dict[str, int]] = {}
        with Database1CD(cd) as db:
            for name in sorted(db.tables):
                rows, nbytes = db.table_stats(name)
                tables[name] = {'rows': rows, 'bytes': nbytes}
        meta = {'version': '8.x', 'tables': tables}
    print(json.dumps(meta, ensure_ascii=False, indent=2, default=str))
    return 0


# ---- extract ----

def _extract_77(source_dir: str, encoding: str, limit: int,
                only: list[str]) -> list[dict[str, Any]]:
    from .base_reader import Base77
    reader = Base77(Path(source_dir), encoding=encoding).data
    objs: list[dict[str, Any]] = []
    for table_id, recs in reader.references().items():
        obj_type = f'Справочник.{table_id}'
        if only and not any(o in obj_type for o in only):
            continue
        for rec in recs:
            if not rec:
                continue
            objs.append({
                OBJ_TYPE: obj_type,
                OBJ_ID: str(rec[0]),
                OBJ_KEY: [str(v) for v in rec[1:3]],
                OBJ_ATTRS: {'_code': rec[1] if len(rec) > 1 else None,
                            '_descr': rec[2] if len(rec) > 2 else None},
                OBJ_REFS: {},
            })
            if limit and len(objs) >= limit:
                return objs
    return objs


def _extract_8x(source_dir: str, limit: int, only: list[str]) -> list[dict[str, Any]]:
    from .source_8x_file import Database1CD, read_table
    cd = Path(source_dir) / '1Cv8.1CD'
    objs: list[dict[str, Any]] = []
    with Database1CD(cd) as db:
        names = sorted(db.tables)
    for name in names:
        if only and not any(o.lower() in name.lower() for o in only):
            continue
        for i, rec in enumerate(read_table(cd, name)):
            objs.append({
                OBJ_TYPE: f'Таблица.{name}',
                OBJ_ID: str(i),
                OBJ_KEY: [],
                OBJ_ATTRS: rec,
                OBJ_REFS: {},
            })
            if limit and len(objs) >= limit:
                return objs
    return objs


def cmd_extract(args: argparse.Namespace) -> int:
    """Чтение 7.7/8.x -> intermediate JSON (--encoding, --anonymize-fields, --limit, --objects)."""
    # конфиг-файл (onec.toml) как источник дефолтов (Фаза 20)
    from .config import ProjectConfig
    cfg = ProjectConfig.load()
    encoding = args.source_encoding
    if args.source_encoding in ('cp866', '') and cfg.source_encoding:
        encoding = cfg.source_encoding
    limit = args.limit or cfg.limit
    only = [o.strip() for o in args.objects.split(',')] if args.objects else []
    ver = _detect_version(args.source_dir)
    if ver == '77':
        objs = _extract_77(args.source_dir, encoding, limit, only)
    else:
        objs = _extract_8x(args.source_dir, limit, only)
    if args.anonymize_fields:
        from .anonymizer import Anonymizer
        fields = [f.strip() for f in args.anonymize_fields.split(',') if f.strip()]
        anon = Anonymizer(fields=fields)
        for obj in objs:
            obj[OBJ_ATTRS] = anon.apply(obj[OBJ_ATTRS])
    save_json_batch(objs, args.out)
    print(json.dumps({'ok': True, 'objects': len(objs), 'file': args.out},
                     ensure_ascii=False))
    return 0


# ---- map ----

def cmd_map(args: argparse.Namespace) -> int:
    """Правила маппинга: валидация (--rules-file) или промпт LLM (--llm-prompt, без вызова)."""
    if args.llm_prompt:
        if not args.meta_source or not args.meta_target or not args.out:
            return _err('--llm-prompt требует --meta-source, --meta-target, --out')
        ms: dict[str, Any] = json.loads(Path(args.meta_source).read_text(encoding='utf-8'))
        mt: dict[str, Any] = json.loads(Path(args.meta_target).read_text(encoding='utf-8'))
        prompt = build_prompt(ms, mt)
        Path(args.out).write_text(prompt, encoding='utf-8')
        print(json.dumps({'ok': True, 'prompt_file': args.out}, ensure_ascii=False))
        return 0
    if not args.rules_file:
        return _err('укажите --rules-file или --llm-prompt')
    try:
        rules = load_rules(args.rules_file)
    except MappingError as exc:
        return _err(str(exc))
    print(json.dumps({'ok': True, 'objects': len(rules.get('objects', [])),
                      'enums': len(rules.get('enums', {}))}, ensure_ascii=False))
    return 0


# ---- transform ----

def cmd_transform(args: argparse.Namespace) -> int:
    """Применение правил к intermediate (--preview — dry-run первых N строк)."""
    try:
        rules = load_rules(args.rules_file)
    except MappingError as exc:
        return _err(str(exc))
    objs = load_json_batch(args.input)
    resolver = RefResolver()
    resolver.build(objs)
    rule_map = {r['source']: r for r in rules.get('objects', [])}
    out: list[dict[str, Any]] = []
    problems: list[str] = []
    for obj in objs:
        rule = rule_map.get(obj[OBJ_TYPE])
        if rule is None:
            problems.append(f'нет правила для {obj[OBJ_TYPE]}')
            continue
        try:
            out.append(transform_object(obj, rule, resolver, rules.get('enums')))
        except TransformError as exc:
            problems.append(str(exc))
    vr = validate_batch(out)
    if not vr.ok:
        for e in vr.errors:
            print(f'  - {e}', file=sys.stderr)
        return _err('валидация не пройдена')
    if args.preview:
        print(json.dumps(out[:args.preview], ensure_ascii=False, indent=2,
                         default=str))
        return 0
    save_json_batch(out, args.out)
    print(json.dumps({'ok': True, 'objects': len(out), 'file': args.out,
                      'problems': problems}, ensure_ascii=False))
    return 0


# ---- load ----

async def _http_load(objs: list[dict[str, Any]],
                     args: argparse.Namespace) -> tuple[int, int, list[str]]:
    from .config import ProjectConfig
    cfg = ProjectConfig.load()
    api_key = args.api_key or cfg._raw.get('api_key', '') or cfg._raw.get('target_api_key', '')
    retries = args.retries or cfg.retries
    token_url = args.token_url or cfg.token_url
    client_id = args.client_id or cfg.client_id
    client_secret = args.client_secret or cfg.client_secret
    client = HttpClient83(args.http, retries=retries,
                          api_key=api_key or None,
                          token_url=token_url or None,
                          client_id=client_id or None,
                          client_secret=client_secret or None)
    try:
        results = await client.load(objs, args.source_ib, args.target_ib)
    finally:
        await client.aclose()
    created = sum(r.created for r in results)
    updated = sum(r.updated for r in results)
    errors = [e for r in results for e in r.errors]
    return created, updated, errors


def cmd_load(args: argparse.Namespace) -> int:
    """Загрузка батчей в приёмник: файл (--target), HTTP (--http) или прямая
    запись в копию 1CD (--direct, Фаза 13 zero-setup)."""
    objs = load_json_batch(args.input)
    if args.direct:
        from .load_8x import LoadError, load_direct

        try:
            rep = load_direct(args.direct, objs, workdir=args.workdir or None)
        except LoadError as exc:
            return _err(str(exc))
        print(json.dumps(rep, ensure_ascii=False, default=str))
        return 0
    if args.http:
        created, updated, errors = asyncio.run(_http_load(objs, args))
        if errors:
            for e in errors[:10]:
                print(f'  - {e}', file=sys.stderr)
            return _err(f'ошибки загрузки: {len(errors)}')
        print(json.dumps({'ok': True, 'created': created, 'updated': updated},
                         ensure_ascii=False))
        return 0
    target = Path(args.target)
    if target.is_dir() or args.target.endswith(('/', '\\')):
        target = target / 'load.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    save_json_batch(objs, target)
    print(json.dumps({'ok': True, 'objects': len(objs), 'file': str(target)},
                     ensure_ascii=False))
    return 0


# ---- status ----

def cmd_status(args: argparse.Namespace) -> int:
    """Состояние пайплайна в project-dir (коннекторы, кеш, последний шаг, метрики).

    Загружает сохранённый project.json (binding), кеш сканируется в каталоге
    проекта; коннекторы/последний шаг — состояние текущего процесса.
    """
    from .cache import Cache
    from .inspect_target import ProjectBinding, ProjectError
    from .mcp_server import PipelineState

    project = Path(args.project_dir)
    st = PipelineState(project)
    st.cache = Cache(project / '.onec_cache')
    try:
        st.binding = ProjectBinding.load(project)
    except ProjectError:
        pass
    print(json.dumps(st.step_status(), ensure_ascii=False, indent=2))
    return 0


# ---- Фаза 11: query / guid-diff / config-versions ----

def cmd_query(args: argparse.Namespace) -> int:
    """SQL-подобная выборка записей таблицы 1CD (консоль запросов)."""
    from .query import query_table_sql
    from .source_8x_file import Database1CD

    try:
        cd = Path(args.source_dir) / '1Cv8.1CD'
        if not cd.is_file():
            return _err(f'нет 1Cv8.1CD в {args.source_dir}')
        with Database1CD(cd) as db:
            rows = query_table_sql(db, args.table, select=args.select,
                                   where=args.where, order_by=args.order_by,
                                   limit=args.limit)
    except QueryError as exc:
        return _err(str(exc))
    print(json.dumps({'ok': True, 'table': args.table, 'count': len(rows),
                      'rows': rows}, ensure_ascii=False, default=str))
    return 0


def cmd_guid_diff(args: argparse.Namespace) -> int:
    """Сверка двух баз по GUID: объекты и таблицы (полнота переноса)."""
    from .guid_diff import guid_diff
    from .source_8x_file import FormatError

    try:
        report = guid_diff(args.source_dir, args.target_dir)
    except FormatError as exc:
        return _err(str(exc))
    except (OSError, ValueError) as exc:
        return _err(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_config_versions(args: argparse.Namespace) -> int:
    """Версии конфигурации: формат, ИБ/платформа, дифф CONFIG↔CONFIGSAVE."""
    from .config_versions import config_versions

    try:
        report = config_versions(Path(args.source_dir) / '1Cv8.1CD')
    except (OSError, ValueError) as exc:
        return _err(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Диагностика окружения (Фаза 17): версии/зависимости/кеш.

    Не падает на отсутствующих компонентах — печатает статус и возвращает
    ＞0, если есть проблемы, мешающие работе.
    """
    import importlib.metadata as md
    import platform
    import shutil

    problems = 0

    def row(name: str, ok: bool, detail: str = '') -> None:
        nonlocal problems
        mark = 'OK ' if ok else 'WARN'
        print(f'  [{mark}] {name}{(": " + detail) if detail else ""}')
        if not ok:
            problems += 1

    print(f'onec-converter doctor (python {platform.python_version()})')
    # версия mcp — совместимость 1.x
    try:
        mcp_ver = md.version('mcp')
        ok = mcp_ver.split('.')[0] == '1'
        row('mcp', ok, f'{mcp_ver}{" (2.x несовместим — нужен 1.x)" if not ok else ""}')
    except md.PackageNotFoundError:
        row('mcp', False, 'не установлен')
    # PyYAML
    try:
        import yaml  # type: ignore[import-untyped]  # noqa: F401
        row('PyYAML', True, md.version('PyYAML'))
    except (ImportError, ModuleNotFoundError):
        row('PyYAML', False, 'не установлен — dump_metadata(fmt=yaml) не работает')
    # дисковый кеш
    cache_dir = Path('.onec_cache')
    try:
        cache_dir.mkdir(exist_ok=True)
        free = shutil.disk_usage(cache_dir).free
        free_gb = free / (1024 ** 3)
        row('cache', True, f'.onec_cache: {free_gb:.1f} ГБ свободно')
    except OSError as exc:
        row('cache', False, f'недоступен: {exc}')
    # CLI-зависимости (необязательные модули)
    for mod, label in [('olefile', 'olefile'), ('openpyxl', 'openpyxl'),
                       ('httpx', 'httpx')]:
        try:
            __import__(mod)
            row(label, True)
        except (ImportError, ModuleNotFoundError):
            row(label, False, 'не установлен')
    print('doctor: ' + ('все проверки пройдены' if problems == 0
                        else f'{problems} проблема(ы) выявлено'))
    return 0 if problems == 0 else 1


def cmd_cache(args: argparse.Namespace) -> int:
    """Кеш: stats — статистика, clear — полная очистка (Фаза 18)."""
    from .cache import Cache

    c = Cache(Path(args.root_dir if getattr(args, 'root_dir', '') else '.onec_cache'))
    action = getattr(args, 'sub', 'stats') or 'stats'
    if action == 'clear':
        c.clear()
        print(json.dumps({'ok': True, 'action': 'clear'}))
    else:
        st = c.stats()
        st['ok'] = True
        print(json.dumps(st, ensure_ascii=False))
    return 0


def cmd_dump_records(args: argparse.Namespace) -> int:
    """Вывод первых N строк таблицы 1CD в JSON/CSV (Фаза 20, для отладки правил)."""
    from .source_8x_file import Database1CD, decode_field

    cd = Path(args.source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return _err(f'нет 1Cv8.1CD в {args.source_dir}')
    limit = args.limit
    with Database1CD(cd) as db:
        t = db.tables.get(args.table)
        if t is None:
            return _err(f'нет таблицы {args.table!r}')
        rows: list[dict[str, Any]] = []
        for i, row in enumerate(db.table_rows(t)):
            if i >= limit:
                break
            rec: dict[str, Any] = {}
            for fname, fdef in t.fields.items():
                try:
                    rec[fname] = _jsonable(decode_field(fdef, row[fdef.offset:fdef.offset + fdef.size]))
                except (IndexError, ValueError, UnicodeDecodeError):
                    rec[fname] = None
            rows.append(rec)
    if args.format == 'csv':
        import csv
        import io
        out = io.StringIO()
        if rows:
            w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(out.getvalue().rstrip())
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
    return 0


def _jsonable(v: Any) -> Any:
    return str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v


def cmd_metrics(_args: argparse.Namespace) -> int:
    """Метрики в формате Prometheus (Фаза 21): кеш, операции."""
    from .cache import Cache
    from .metrics import render_from_timings
    from .timings import Timings

    print(render_from_timings(Timings().snapshot(), Cache().stats()))
    return 0


# ---- entry point ----

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='onec-converter',
        description='Перенос данных между ИБ 1С (CLI без MCP-клиента).')
    p.add_argument('--version', action='version',
                  version=__version__)
    sub = p.add_subparsers(dest='command', required=True)

    p_inspect = sub.add_parser('inspect', help='Метаданные источника')
    p_inspect.add_argument('--source-dir', required=True)
    p_inspect.add_argument('--source-encoding', default='cp866')

    p_extract = sub.add_parser('extract', help='Извлечение данных в intermediate JSON')
    p_extract.add_argument('--source-dir', required=True)
    p_extract.add_argument('--source-encoding', default='cp866')
    p_extract.add_argument('--out', required=True)
    p_extract.add_argument('--anonymize-fields', default='')
    p_extract.add_argument('--limit', type=int, default=0)
    p_extract.add_argument('--objects', default='')

    p_map = sub.add_parser('map', help='Правила маппинга (TOON)')
    p_map.add_argument('--rules-file', default='')
    p_map.add_argument('--llm-prompt', action='store_true')
    p_map.add_argument('--meta-source', default='')
    p_map.add_argument('--meta-target', default='')
    p_map.add_argument('--out', default='')

    p_transform = sub.add_parser('transform', help='Применение правил к intermediate')
    p_transform.add_argument('--rules-file', required=True)
    p_transform.add_argument('--input', required=True)
    p_transform.add_argument('--out', default='')
    p_transform.add_argument('--preview', type=int, default=0)

    p_load = sub.add_parser('load', help='Загрузка в приёмник (файл/HTTP/прямая запись)')
    p_load.add_argument('--input', required=True)
    p_load.add_argument('--target', default='')
    p_load.add_argument('--http', default='')
    p_load.add_argument('--direct', default='',
                        help='каталог приёмника 8.x: запись в копию 1CD (Фаза 13)')
    p_load.add_argument('--workdir', default='',
                        help='каталог для копии приёмника (--direct)')
    p_load.add_argument('--source-ib', default='source')
    p_load.add_argument('--target-ib', default='target')
    p_load.add_argument('--api-key', default='',
                        help='ключ аутентификации приёмника (X-API-Key, Фаза 18)')
    p_load.add_argument('--token-url', default='',
                        help='OAuth2 token_url (client-credentials): Bearer-режим (Фаза 22)')
    p_load.add_argument('--client-id', default='',
                        help='OAuth2 client_id (при --token-url)')
    p_load.add_argument('--client-secret', default='',
                        help='OAuth2 client_secret (при --token-url)')
    p_load.add_argument('--retries', type=int, default=0,
                        help='число повторов HTTP (0 = из конфига/по умолчанию)')

    p_status = sub.add_parser('status', help='Состояние пайплайна')
    p_status.add_argument('--project-dir', default='.')

    p_query = sub.add_parser('query', help='SQL-подобная выборка таблицы 1CD (Фаза 11)')
    p_query.add_argument('--source-dir', required=True)
    p_query.add_argument('--table', required=True)
    p_query.add_argument('--select', default='*')
    p_query.add_argument('--where', default='')
    p_query.add_argument('--order-by', default='')
    p_query.add_argument('--limit', type=int, default=100)

    p_guid_diff = sub.add_parser('guid-diff', help='Сверка двух баз по GUID (Фаза 11)')
    p_guid_diff.add_argument('--source-dir', required=True)
    p_guid_diff.add_argument('--target-dir', required=True)

    p_config_versions = sub.add_parser('config-versions',
                                       help='Версии конфигурации из файла базы (Фаза 11)')
    p_config_versions.add_argument('--source-dir', required=True)

    sub.add_parser('doctor', help='Диагностика окружения (Фаза 17): зависимости/кеш')

    p_cache = sub.add_parser('cache', help='Кеш: stats / clear (Фаза 18)')
    p_cache.add_argument('sub', nargs='?', default='stats',
                         choices=['stats', 'clear'])
    p_cache.add_argument('--root-dir', default='', help='Каталог кеша')

    p_dump = sub.add_parser('dump-records',
                            help='Первый N строк таблицы 1CD в JSON/CSV (Фаза 20)')
    p_dump.add_argument('--source-dir', required=True)
    p_dump.add_argument('--table', required=True)
    p_dump.add_argument('--limit', type=int, default=20)
    p_dump.add_argument('--format', choices=['json', 'csv'], default='json')

    sub.add_parser('metrics', help='Метрики в формате Prometheus (Фаза 21)')

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        'inspect': cmd_inspect,
        'extract': cmd_extract,
        'map': cmd_map,
        'transform': cmd_transform,
        'load': cmd_load,
        'status': cmd_status,
        'query': cmd_query,
        'guid-diff': cmd_guid_diff,
        'config-versions': cmd_config_versions,
        'doctor': cmd_doctor,
        'cache': cmd_cache,
        'dump-records': cmd_dump_records,
        'metrics': cmd_metrics,
    }
    try:
        handler = handlers.get(args.command or '')
        if handler is None:
            return _err(f'неизвестная команда: {args.command}')
        return handler(args)
    except CLIError as exc:
        return _err(str(exc))
    except (OSError, ValueError) as exc:
        return _err(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
