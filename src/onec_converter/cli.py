"""CLI-обёртка пайплайна onec_converter (без MCP-клиента).

Команды в терминале: inspect, extract, map, transform, load, status.
Только stdlib (argparse); переиспользует модули пайплайна, не дублируя логику.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .audit import get_audit, read_audit, set_audit
from .config import DEFAULT_SOURCE_ENCODING
from .http_client import HttpClient83
from .intermediate import (
    OBJ_ATTRS,
    OBJ_ID,
    OBJ_KEY,
    OBJ_REFS,
    OBJ_TYPE,
    load_json_batch,
    save_json_batch,
    save_json_stream,
)
from .mapping import MappingError, build_prompt, load_rules
from .objects_filter import ObjectSpec, parse_objects, selects
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
    if _resolve_pretty(args):
        from .terminal import render_table

        if ver == '77':
            print(f'Версия: 7.7; разделов: {len(meta["sections"])}; '
                  f'справочников: {len(meta["references_tables"])}; '
                  f'констант: {meta["constants"]}')
            return 0
        print(render_table(
            ['Таблица', 'Строк', 'Байт'],
            [[n, meta['tables'][n]['rows'], meta['tables'][n]['bytes']]
             for n in sorted(meta['tables'])], max_col=60))
        return 0
    print(json.dumps(meta, ensure_ascii=False, indent=2, default=str))
    return 0


# ---- extract ----

def _extract_77(source_dir: str, encoding: str, limit: int,
                specs: list[ObjectSpec]) -> list[dict[str, Any]]:
    from .base_reader import Base77
    reader = Base77(Path(source_dir), encoding=encoding).data
    objs: list[dict[str, Any]] = []
    for table_id, recs in reader.references().items():
        obj_type = f'Справочник.{table_id}'
        if specs and not selects(specs, 'Справочник', str(table_id)):
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


def _extract_8x(source_dir: str, limit: int,
                specs: list[ObjectSpec], workers: int = 1) -> list[dict[str, Any]]:
    """8.x: без фильтра — все таблицы (совместимость); с фильтром — только
    таблицы выбранных объектов конфигурации (read_metadata: kind+имя) или
    физические таблицы через `Таблица.*`. При workers>1 — параллельное
    чтение независимых таблиц (порядок строк сохраняется)."""
    from .source_8x_file import Database1CD, FormatError, read_metadata, read_table
    cd = Path(source_dir) / '1Cv8.1CD'
    with Database1CD(cd) as db:
        names = sorted(db.tables)
    # маппинг физическая таблица -> (kind, имя) объекта конфигурации
    meta_by_table: dict[str, tuple[str, str]] = {}
    if specs:
        try:
            for o in read_metadata(cd)['objects']:
                if o.get('table'):
                    meta_by_table[o['table']] = (o['kind'], o['name'])
        except FormatError:
            # база без метаданных (синтетика): только физический фильтр Таблица.*
            pass

    selected: list[str] = []
    for name in names:
        if specs:
            info = meta_by_table.get(name)
            if info:
                kind, obj_name = info
                if not selects(specs, kind, obj_name, table=name):
                    continue
            elif not selects(specs, 'Таблица', name, table=name):
                # служебная/неконфигурационная таблица — только через Таблица.*
                continue
        selected.append(name)

    if not selected:
        return []

    import threading
    lock = threading.Lock()
    counter = 0

    def _rows(name: str) -> list[dict[str, Any]]:
        nonlocal counter
        out: list[dict[str, Any]] = []
        for i, rec in enumerate(read_table(cd, name)):
            out.append({
                OBJ_TYPE: f'Таблица.{name}',
                OBJ_ID: str(i),
                OBJ_KEY: [],
                OBJ_ATTRS: rec,
                OBJ_REFS: {},
            })
            with lock:
                if limit and counter >= limit:
                    return out
                counter += 1
        return out

    if workers > 1 and len(selected) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as ex:
            # map сохраняет порядок входных имён -> детерминированный вывод
            chunks = list(ex.map(_rows, selected))
        objs = [o for chunk in chunks for o in chunk]
    else:
        objs = []
        for name in selected:
            objs.extend(_rows(name))
            if limit and len(objs) >= limit:
                break
    if limit:
        return objs[:limit]
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
    try:
        specs = parse_objects(
            [o.strip() for o in args.objects.split(',')]) if args.objects else []
    except ValueError as exc:
        raise CLIError(str(exc)) from exc
    skind = getattr(args, 'source_kind', '1cd') or '1cd'
    if skind != '1cd':
        from .sql_source import SqlSourceError, build_sql_source
        if not args.source_url:
            return _err('--source-url обязателен при --source-kind != 1cd')
        try:
            src = build_sql_source(skind, args.source_url)
            try:
                objs = list(src.read_objects())
            finally:
                src.close()
        except SqlSourceError as exc:
            return _err(str(exc))
    else:
        ver = _detect_version(args.source_dir)
        if ver == '77':
            objs = _extract_77(args.source_dir, encoding, limit, specs)
        else:
            objs = _extract_8x(args.source_dir, limit, specs,
                               workers=getattr(args, 'workers', 1))
    if limit and len(objs) > limit:
        objs = objs[:limit]
    if args.anonymize_fields:
        from .anonymizer import Anonymizer
        fields = [f.strip() for f in args.anonymize_fields.split(',') if f.strip()]
        anon = Anonymizer(fields=fields)
        for obj in objs:
            obj[OBJ_ATTRS] = anon.apply(obj[OBJ_ATTRS])
    # аудит (Фаза 25): каждый извлечённый объект — тип, идентификатор, время
    audit = get_audit()
    for obj in objs:
        audit.info('extract', obj=str(obj.get(OBJ_TYPE, '')),
                   guid=str(obj.get(OBJ_ID, '')), result='ok')
    # стриминговое сохранение: большие базы не держим целиком в памяти
    save_json_stream(objs, args.out)
    print(json.dumps({'ok': True, 'objects': len(objs), 'file': args.out},
                     ensure_ascii=False))
    _done_note(f'извлечено объектов: {len(objs)} -> {args.out}')
    return 0


# ---- map ----

def cmd_map(args: argparse.Namespace) -> int:
    """Правила маппинга: валидация (--rules-file), промпт LLM (--llm-prompt)
    или --init (шаблон правил из метаданных источника, U12)."""
    if getattr(args, 'init', False):
        if not args.meta_source or not args.out:
            return _err('--init требует --meta-source и --out')
        init_meta: dict[str, Any] = json.loads(
            Path(args.meta_source).read_text(encoding='utf-8'))
        objects_out: list[dict[str, Any]] = []
        for o in init_meta.get('objects') or []:
            kind = o.get('kind') or ''
            name = o.get('name') or ''
            if not kind or not name:
                continue
            src = f'{kind}.{name}'
            attrs: dict[str, str] = {
                (a.get('name') or ''): (a.get('name') or '')
                for a in (o.get('attributes') or [])
            }
            objects_out.append({'source': src, 'target': '',
                                'attributes': attrs})
        schema = {'version': 1, 'objects': objects_out, 'enums': {}}
        Path(args.out).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'ok': True, 'out': args.out,
                          'objects': len(objects_out)}, ensure_ascii=False))
        return 0
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
            get_audit().info('transform', obj=str(obj[OBJ_TYPE]),
                             rule=str(rule.get('source', '')), result='ok')
        except TransformError as exc:
            get_audit().error('transform', obj=str(obj[OBJ_TYPE]),
                              rule=str(rule.get('source', '')), result='error',
                              detail=str(exc))
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
    _done_note(f'преобразовано объектов: {len(out)} -> {args.out}'
               + (f' ({len(problems)} проблем)' if problems else ''))
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
    secret_cfg = cfg.secret or cfg._raw.get('secret', '')
    secret = _resolve_secret(args.secret) or secret_cfg
    client = HttpClient83(args.http, retries=retries,
                          api_key=api_key or None,
                          token_url=token_url or None,
                          client_id=client_id or None,
                          client_secret=client_secret or None,
                          secret=secret or None)
    try:
        results = await client.load(objs, args.source_ib, args.target_ib)
    finally:
        await client.aclose()
    created = sum(r.created for r in results)
    updated = sum(r.updated for r in results)
    errors = [e for r in results for e in r.errors]
    return created, updated, errors


def cmd_export_kd3(args: argparse.Namespace) -> int:
    """Экспорт правил TOON в XML в стиле КД3 (Фаза 29.2) — ревью/перенос."""
    from .kd3_export import Kd3Error, export_kd3

    try:
        rep = export_kd3(args.rules, args.out)
    except Kd3Error as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False))
    return 0


def cmd_shell(args: argparse.Namespace) -> int:
    """Интерактивная оболочка для исследования базы 1CD (Фаза 39)."""
    from .repl import ReplError, run_shell

    try:
        return run_shell(args.source_dir)
    except ReplError as exc:
        return _err(str(exc))


def cmd_pii_report(args: argparse.Namespace) -> int:
    """Отчёт по анонимизации ПДн (152-ФЗ / 152 УЗ), Фаза 37."""
    from .gdpr_152_report import PiiReportError, gdpr_report

    try:
        rep = gdpr_report(args.audit_file, args.rules_file or None,
                          profile=args.profile)
    except PiiReportError as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


def cmd_mint_token(args: argparse.Namespace) -> int:
    """Выпуск локального Bearer-токена (HS256 JWT) на общем секрете (Фаза 33).

    --dry-run — показать payload (claims) без подписи; --json — вывод
    {'token','exp'} для скриптовой интеграции (Фаза 45).
    """
    from .jwt_auth import mint_jwt

    secret = _resolve_secret(args.secret)
    if not secret:
        return _err('не задан секрет: --secret, ONEC_SECRET или вводом (E3)')
    if getattr(args, 'dry_run', False):
        payload = {'iss': args.issuer, 'sub': 'onec-loader',
                   'iat': int(time.time()), 'exp': int(time.time()) + args.exp_min * 60}
        header: dict[str, object] = {'alg': 'HS256', 'typ': 'JWT'}
        kid = getattr(args, 'kid', '') or ''
        if kid:
            header['kid'] = kid
        print(json.dumps({'header': header, 'payload': payload},
                         ensure_ascii=False, indent=2))
        return 0
    token = mint_jwt(secret, args.issuer, args.exp_min * 60,
                      kid=getattr(args, 'kid', '') or None)
    if getattr(args, 'json', False):
        print(json.dumps({'token': token,
                          'exp': int(time.time()) + args.exp_min * 60},
                         ensure_ascii=False))
    else:
        print(token)
    return 0


def cmd_ai_map(args: argparse.Namespace) -> int:
    """Авто-маппинг схем двух баз -> правила TOON (Фаза 45, обёртка MCP-тула)."""
    from .ai_skills import auto_map_schemas
    from .source_8x_file import read_metadata

    try:
        src = Path(args.source_dir) / '1Cv8.1CD'
        tgt = Path(args.target_dir) / '1Cv8.1CD'
        if not src.is_file() or not tgt.is_file():
            return _err('нет 1Cv8.1CD в --source-dir/--target-dir')
        res = auto_map_schemas(read_metadata(src), read_metadata(tgt))
        rules = res['rules']
        if args.objects:
            from .objects_filter import parse_objects, selects

            specs = parse_objects(args.objects.split(','))
            kept = []
            for r in rules:
                if '.' not in r['source']:
                    kept.append(r)
                    continue
                k, n = r['source'].split('.', 1)
                if selects(specs, k, n):
                    kept.append(r)
            rules = kept
    except Exception as exc:  # noqa: BLE001 — показать как ошибку CLI
        return _err(f'ai-map: {exc}')
    rules_doc = {'version': 1, 'objects': rules, 'enums': {}}
    if args.out:
        Path(args.out).write_text(
            json.dumps(rules_doc, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'ok': True, 'out': args.out,
                          'matched': res['matched'],
                          'unmatched': res['unmatched']}, ensure_ascii=False))
    else:
        print(json.dumps(rules_doc, ensure_ascii=False, indent=2))
    return 0


def cmd_ai_explain(args: argparse.Namespace) -> int:
    """Объяснение причин расхождений структур (Фаза 45)."""
    from .ai_skills import explain_diff
    from .mcp_server import diff_structures
    from .source_8x_file import read_metadata

    try:
        src = Path(args.source_dir) / '1Cv8.1CD'
        tgt = Path(args.target_dir) / '1Cv8.1CD'
        if not src.is_file() or not tgt.is_file():
            return _err('нет 1Cv8.1CD в --source-dir/--target-dir')
        reasons = explain_diff(diff_structures(
            read_metadata(src), read_metadata(tgt)))
    except Exception as exc:  # noqa: BLE001 — показать как ошибку CLI
        return _err(f'ai-explain: {exc}')
    for r in reasons:
        print(r)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Сверка источник↔приёмник (Фаза 48, U1/U9): каждый объект источника
    должен присутствовать в приёмнике с теми же ключом и атрибутами.

    --input — объекты источника (intermediate JSON, напр. extract.json),
    --target — объекты приёмника (те же объекты, прочитанные из приёмника
    после load — например extract из целевой ИБ). --objects — фильтр по
    типу/группе (как в extract). --json — машиночитаемый отчёт для CI.
    rc: 0 — полное совпадение, 1 — есть расхождения.
    """
    from .intermediate import load_json_batch
    from .objects_filter import parse_objects, selects
    from .verify import verify as _verify

    try:
        src_objs = load_json_batch(args.input)
        tgt_objs = load_json_batch(args.target)
    except (OSError, ValueError) as exc:
        return _err(f'verify: не удалось прочитать объекты: {exc}')
    if args.objects:
        specs = parse_objects([s for s in args.objects.split(',') if s.strip()])

        def _keep(o: dict[str, Any]) -> bool:
            t = o.get('type', '') or ''
            if '.' not in t:
                return False
            k, n = t.split('.', 1)
            return selects(specs, k, n)

        src_objs = [o for o in src_objs if _keep(o)]
        tgt_objs = [o for o in tgt_objs if _keep(o)]
    rep = _verify(src_objs, tgt_objs)
    out: dict[str, object] = {
        'ok': rep.full,
        'total_source': rep.total_source,
        'total_target': rep.total_target,
        'matched': rep.matched,
        'missing': rep.missing[:50],
        'mismatched': rep.mismatched[:50],
        'missing_total': len(rep.missing),
        'mismatched_total': len(rep.mismatched),
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f'verify: {rep.matched}/{rep.total_source} совпало '
              f'(missing={len(rep.missing)}, mismatched={len(rep.mismatched)})')
        for m in rep.missing[:10]:
            print(f'  отсутствует: {m}')
        for m in rep.mismatched[:10]:
            print(f'  различается: {m}')
    return 0 if rep.full else 1


def cmd_rules_diff(args: argparse.Namespace) -> int:
    """Сравнение двух правил TOON (Фаза 48): что изменилось между версиями
    правил — объекты/атрибуты добавлены, удалены, изменены."""
    try:
        a: dict[str, Any] = json.loads(Path(args.a).read_text(encoding='utf-8'))
        b: dict[str, Any] = json.loads(Path(args.b).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return _err(f'rules-diff: {exc}')
    ao = {r['source']: r for r in (a.get('objects') or [])}
    bo = {r['source']: r for r in (b.get('objects') or [])}
    added = sorted(set(bo) - set(ao))
    removed = sorted(set(ao) - set(bo))
    changed = []
    for name in sorted(set(ao) & set(bo)):
        if ao[name] != bo[name]:
            changed.append(name)
    out = {'added': added, 'removed': removed, 'changed': changed,
           'changed_total': len(changed)}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for name in added:
            print(f'+ {name}')
        for name in removed:
            print(f'- {name}')
        for name in changed:
            print(f'~ {name}')
        print(f'rules-diff: +{len(added)} -{len(removed)} ~{len(changed)}')
    return 0


def cmd_sonar_report(args: argparse.Namespace) -> int:
    """Отчёт ruff в sonar-формате (Фаза 28): --format xml|json, --target,
    --out — запись в файл для CI-артефакта. Контракт потоков (аудит раунда 6,
    A8): тело отчёта — stdout, метаданные {ok,total,format} — stderr."""
    from .sonar_report import SonarReportError, sonar_report

    try:
        rep = sonar_report(args.target, args.format)
    except SonarReportError as exc:
        return _err(str(exc))
    if args.out:
        Path(args.out).write_text(rep['body'], encoding='utf-8')
    else:
        print(rep['body'])
    print(json.dumps({'ok': True, 'total': rep['total'],
                      'format': rep['format']}, ensure_ascii=False),
          file=sys.stderr)
    return 0


def cmd_dump_report(args: argparse.Namespace) -> int:
    """Экспорт отчёта в S3 (Фаза 27): файл JSON/XLSX -> bucket
    через минимальный SigV4-клиент (--endpoint для S3-совместимых).
    Файл загружается потоково (upload_file, Фаза 49 U36) — не читается
    целиком в память."""
    from .s3_client import S3Error, upload_file

    f = Path(args.file)
    if not f.is_file():
        return _err(f'нет файла отчёта: {args.file}')
    ct = ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          if f.suffix.lower() == '.xlsx' else 'application/json')
    try:
        rep = upload_file(args.s3, f.name, f,
                          access_key=args.key, secret_key=args.secret,
                          endpoint=args.endpoint, region=args.region,
                          content_type=ct)
    except S3Error as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Сводка по ИБ 1CD: число таблиц, строк, объём, locale (Фаза 53, U16)."""
    from .source_8x_file import Database1CD

    cd = Path(args.source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return _err(f'нет 1Cv8.1CD в {args.source_dir}')
    with Database1CD(cd) as db:
        stats = db.table_stats_all()
        total_rows = sum(v[0] for v in stats.values())
        total_bytes = sum(v[1] for v in stats.values())
        rep = {
            'ok': True,
            'tables': len(db.tables),
            'rows': total_rows,
            'bytes': total_bytes,
            'locale': getattr(db, 'locale', ''),
        }
    if _resolve_pretty(args):
        from .terminal import render_table

        print(render_table(['Показатель', 'Значение'], [
            ['Таблиц', rep['tables']],
            ['Строк', rep['rows']],
            ['Объём, байт', rep['bytes']],
            ['Locale', rep['locale']],
        ]))
        return 0
    print(json.dumps(rep, ensure_ascii=False))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    """MCP: список тулов (по умолчанию) или запуск сервера --stdio/--sse
    (аудит раунда 6, C1/U15)."""
    if getattr(args, 'stdio', False) or getattr(args, 'sse', False):
        from .mcp_server import server_main

        transport = 'sse' if getattr(args, 'sse', False) else 'stdio'
        server_main(transport)
        return 0
    from .mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    out = [{'name': t.name, 'description': (getattr(t, 'description', '') or '')}
           for t in sorted(tools, key=lambda t: t.name)]
    print(json.dumps({'ok': True, 'count': len(out), 'tools': out},
                     ensure_ascii=False))
    return 0


def cmd_export_xlsx(args: argparse.Namespace) -> int:
    """Экспорт первых N строк таблицы 1CD в XLSX (Фаза 53, U11)."""
    from .source_8x_file import Database1CD

    cd = Path(args.source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return _err(f'нет 1Cv8.1CD в {args.source_dir}')
    if not args.out:
        return _err('укажите --out для XLSX')
    rows: list[dict[str, object]] = []
    with Database1CD(cd) as db:
        t = db.tables.get(args.table)
        if t is None:
            return _err(f'нет таблицы {args.table!r}')
        assert t is not None
        for i, row in enumerate(db.table_rows(t)):
            if args.limit and i >= args.limit:
                break
            rows.append(_table_row_to_rec(row, t))
    from openpyxl import Workbook
    from openpyxl.styles import Font as XFont

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = (t.name or 'Table')[:31]
    fields = list(t.fields)
    ws.append(fields)  # заголовки
    for c in ws[1]:
        c.font = XFont(bold=True)
    for rec in rows:
        ws.append([rec.get(f) for f in fields])
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    wb.save(outp)
    print(json.dumps({'ok': True, 'path': str(outp), 'rows': len(rows)},
                     ensure_ascii=False))
    return 0


def _notify(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    """Отправка уведомления по завершении load (best-effort, Фаза 27)."""
    from .notify import NotifyError, notify_telegram, send_webhook

    try:
        if args.notify_telegram:
            token, _, chat = args.notify_telegram.partition(':')
            if not chat:
                raise NotifyError('--notify-telegram ждёт token:chat_id')
            res = notify_telegram(token, chat, json.dumps(
                payload, ensure_ascii=False))
        elif args.notify_url:
            res = send_webhook(args.notify_url, payload)
        else:
            return
        if not res.get('ok'):
            print(f'  - уведомление: статус {res.get("status")}',
                  file=sys.stderr)
    except NotifyError as exc:
        print(f'  - {exc}', file=sys.stderr)


def cmd_load(args: argparse.Namespace) -> int:
    """Загрузка батчей в приёмник: файл (--target), HTTP (--http) или прямая
    запись в копию 1CD (--direct, Фаза 13 zero-setup)."""
    objs = load_json_batch(args.input)
    if getattr(args, 'dry_run', False):
        # демо-план без изменения файлов/отправки (Фаза 39)
        plan = {
            'dry_run': True,
            'objects': len(objs),
            'mode': 'direct' if args.direct else ('http' if args.http else 'file'),
            'target': args.direct or args.http or str(args.target),
            'note': 'запись/отправка не выполнялась (--dry-run)',
        }
        print(json.dumps(plan, ensure_ascii=False, default=str))
        return 0
    if args.direct:
        from .load_8x import LoadError, load_direct

        try:
            rep = load_direct(args.direct, objs, workdir=args.workdir or None,
                              snapshot=not args.no_snapshot)
        except LoadError as exc:
            return _err(str(exc))
        if args.index_repair:
            from .index_rebuilder import IndexRepairError, build_repair_script
            try:
                ir = build_repair_script(args.direct)
            except IndexRepairError as exc:
                print(f'  - {exc}', file=sys.stderr)
            else:
                print(f'  - скрипт восстановления индексов: {ir["script"]}'
                      f' (tool={ir["tool_used"]})', file=sys.stderr)
        _notify(args, {'ok': True, 'total': rep.get('total', 0),
                       'tables': rep.get('tables', 0),
                       'mode': 'direct', 'workdir': str(args.workdir or '')})
        print(json.dumps(rep, ensure_ascii=False, default=str))
        return 0
    if args.http:
        created, updated, errors = asyncio.run(_http_load(objs, args))
        if errors:
            for e in errors[:10]:
                print(f'  - {e}', file=sys.stderr)
            return _err(f'ошибки загрузки: {len(errors)}')
        _notify(args, {'ok': True, 'created': created, 'updated': updated,
                       'mode': 'http'})
        print(json.dumps({'ok': True, 'created': created, 'updated': updated},
                         ensure_ascii=False))
        return 0
    if not args.target:
        return _err('нет способа загрузки: укажите --target, --http или --direct')
    target = Path(args.target)
    if target.is_dir() or args.target.endswith(('/', '\\')):
        target = target / 'load.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    save_json_batch(objs, target)
    _notify(args, {'ok': True, 'objects': len(objs),
                   'mode': 'file', 'file': str(target)})
    print(json.dumps({'ok': True, 'objects': len(objs), 'file': str(target)},
                     ensure_ascii=False))
    _done_note(f'загружено объектов: {len(objs)} -> {target}')
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
    if _resolve_pretty(args):
        from .terminal import render_table

        if not rows:
            print('(нет строк)')
            return 0
        headers = list(rows[0].keys())
        print(render_table(headers, [list(r.values()) for r in rows]))
        return 0
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
    if _resolve_pretty(args):
        from .terminal import render_table

        print(f'Объекты: только источник {len(report["objects"]["only_source"])}, '
              f'только приёмник {len(report["objects"]["only_target"])}')
        print(f'Таблицы: только источник {len(report["tables"]["only_source"])}, '
              f'только приёмник {len(report["tables"]["only_target"])}')
        osrc = list(report['objects']['only_source'])
        if osrc:
            print()
            print(render_table(['Только в источнике (объекты)'],
                               [[o] for o in osrc], max_col=60))
        return 0
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
    if getattr(_args, 'fix', False):
        # U13: --fix — создаёт кеш и печатает команды установки недостающего.
        cache_dir.mkdir(exist_ok=True)
        missing = []
        try:
            __import__('olefile')
        except (ImportError, ModuleNotFoundError):
            missing.append('olefile')
        try:
            __import__('openpyxl')
        except (ImportError, ModuleNotFoundError):
            missing.append('openpyxl')
        try:
            __import__('httpx')
        except (ImportError, ModuleNotFoundError):
            missing.append('httpx')
        if missing:
            print('  fix: поставьте недостающие: '
                  f'python -m pip install {" ".join(missing)}')
        else:
            print('  fix: все опциональные зависимости на месте; кеш готов')
    print('doctor: ' + ('все проверки пройдены' if problems == 0
                        else f'{problems} проблема(ы) выявлено'))
    return 0 if problems == 0 else 1


def cmd_cache(args: argparse.Namespace) -> int:
    """Кеш: stats — статистика, trim — LRU-эвикция, clear — очистка (Фаза 18/48)."""
    from .cache import Cache

    c = Cache(Path(args.root_dir if getattr(args, 'root_dir', '') else '.onec_cache'))
    action = getattr(args, 'sub', 'stats') or 'stats'
    if action == 'clear':
        c.clear()
        print(json.dumps({'ok': True, 'action': 'clear'}))
    elif action == 'trim':
        removed = c.trim(max_bytes=getattr(args, 'max_bytes', None) or None,
                         ttl_seconds=getattr(args, 'ttl', None) or None)
        st = c.stats()
        st['ok'] = True
        st['removed'] = removed
        print(json.dumps(st, ensure_ascii=False))
    else:
        st = c.stats()
        st['ok'] = True
        print(json.dumps(st, ensure_ascii=False))
    return 0


def cmd_dump_records(args: argparse.Namespace) -> int:
    """Вывод первых N строк таблицы 1CD в JSON/CSV (Фаза 20, для отладки правил).

    Фаза 49 (U40): потоковый вывод — строки пишутся в stdout по мере чтения,
    а не накапливаются в списке; --max-bytes ограничивает размер вывода.
    """
    from .source_8x_file import Database1CD

    cd = Path(args.source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        return _err(f'нет 1Cv8.1CD в {args.source_dir}')
    limit = args.limit
    max_bytes = getattr(args, 'max_bytes', 0) or 0

    with Database1CD(cd) as db:
        t = db.tables.get(args.table)
        if t is None:
            return _err(f'нет таблицы {args.table!r}')
        assert t is not None

        if args.format == 'csv':
            import csv
            import sys
            w = csv.writer(sys.stdout)
            fields = list(t.fields)
            w.writerow(fields)
            total = sum(len(x) + 1 for x in fields)
            for i, row in enumerate(db.table_rows(t)):
                if i >= limit:
                    break
                rec = _table_row_to_rec(row, t)
                line = ','.join(str(rec[f]) for f in fields)
                if max_bytes and total + len(line) > max_bytes:
                    break
                w.writerow([rec[f] for f in fields])
                total += len(line) + 1
            return 0
        import sys
        out = sys.stdout
        out.write('[')
        first = True
        total = 0
        for i, row in enumerate(db.table_rows(t)):
            if i >= limit:
                break
            rec = _table_row_to_rec(row, t)
            chunk = json.dumps(rec, ensure_ascii=False, default=str)
            if max_bytes and total + len(chunk) > max_bytes:
                break
            out.write(('' if first else ',') + chunk)
            first = False
            total += len(chunk)
        out.write(']\n')
    return 0


def _resolve_secret(flag: str = '', env_name: str = 'ONEC_SECRET') -> str:
    """Секрет не светится в ps/history/логах (аудит раунда 6, E3):
    приоритет — флаг (для CI), затем env ONEC_SECRET, затем (в TTY) ввод
    из stdin без эха в истории. Возвращает '' если ниоткуда не найден."""
    if flag:
        return flag
    v = os.environ.get(env_name, '')
    if v:
        return v
    from .terminal import is_tty

    if is_tty():
        try:
            return input(f'{env_name} (секрет, без эха в истории): ').strip()
        except EOFError:
            return ''
    return ''


def _jsonable(v: Any) -> Any:
    return str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v


def _done_note(msg: str, t0: float | None = None) -> None:
    """Человекочитаемая заметка о завершении шага в stderr (аудит раунда 6,
    F3). Печатается ТОЛЬКО в TTY, чтобы не засорять pipe/JSON-выводы."""
    from .terminal import is_tty

    if not is_tty():
        return
    tail = f' ({(time.perf_counter() - t0):.1f}s)' if t0 is not None else ''
    print(f'[done] {msg}{tail}', file=sys.stderr, flush=True)



def _table_row_to_rec(row: bytes, table: Any) -> dict[str, Any]:
    """Декодировать строку 1CD в JSON-совместимый dict по полям таблицы.

    Единый декодер для dump-records и export-xlsx (аудит раунда 6, B5):
    бинарные/некорректные поля опускаются как None.
    """
    from .source_8x_file import decode_field

    rec: dict[str, Any] = {}
    for fname, fdef in table.fields.items():
        try:
            rec[fname] = _jsonable(decode_field(
                fdef, row[fdef.offset:fdef.offset + fdef.size]))
        except (IndexError, ValueError, UnicodeDecodeError):
            rec[fname] = None
    return rec


def cmd_metrics(_args: argparse.Namespace) -> int:
    """Метрики в формате Prometheus (Фаза 21/38): кеш, операции, прогресс."""
    from .cache import Cache
    from .metrics import render_from_timings
    from .progress import get_progress
    from .timings import Timings

    base = render_from_timings(Timings().snapshot(), Cache().stats())
    print(base)
    print(get_progress().render_prometheus())
    return 0


def cmd_clone_db(args: argparse.Namespace) -> int:
    """Полная копия файловой ИБ (1Cv8.1CD) в новый каталог + кеш-сброс
    (Фаза 24). --with-rules — сценарий «стенд»: база + правила маппинга."""
    from .clone_db import CloneError, clone_db

    try:
        rep = clone_db(args.source_dir, args.target_dir, args.with_rules)
    except CloneError as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False, default=str))
    return 0


def cmd_techlog(args: argparse.Namespace) -> int:
    """Техжурнал 1С как источник событий (Фаза 26): каталог логов,
    фильтры --process/--event/--level-min, --tail, --out JSON."""
    from .source_techlog import TechLog, TechLogError

    try:
        rep = TechLog(args.source_dir).read_events(
            process=args.process, event=args.event,
            level_min=args.level_min, tail=args.tail, out_file=args.out)
    except TechLogError as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False, default=str))
    return 0


def cmd_fetch_config(args: argparse.Namespace) -> int:
    """Релиз конфигурации (XML-выгрузка) как источник метаданных
    (Фаза 26): {objects: [kind, name, uuid]} без платформы."""
    from .fetch_config import FetchConfigError, fetch_config

    try:
        rep = fetch_config(args.source, args.out)
    except FetchConfigError as exc:
        return _err(str(exc))
    print(json.dumps(rep, ensure_ascii=False, default=str))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Просмотр/фильтр журнала. Контракт потоков (аудит раунда 6, A3):
    --json пишет записи в stdout построчно (ndjson), а counts/total — в stderr,
    чтобы stdout был чистым машинопотоком без примесей."""
    try:
        recs = read_audit(args.file)
    except (OSError, ValueError) as exc:
        return _err(f'audit: {exc}')
    if args.level:
        recs = [r for r in recs if r['level'] == args.level.upper()]
    if args.op:
        recs = [r for r in recs if r['operation'] == args.op]
    if args.obj:
        recs = [r for r in recs if args.obj in r['obj']]
    if args.tail:
        recs = recs[-args.tail:]
    if getattr(args, 'csv_out', ''):  # комплаенс-выгрузка (Фаза 48)
        import csv as _csv

        out = Path(args.csv_out)
        fields = ['ts', 'level', 'operation', 'obj', 'result', 'guid', 'rule']

        def _safe(v: str) -> str:
            """Экранировать формульную инъекцию в Excel (аудит раунда 6, A7/E2):
            значение, начинающееся с '=','+','-','@', безвредно префиксуется \t."""
            s = str(v)
            if s.startswith(('=', '+', '-', '@')):
                return '\t' + s
            return s

        with out.open('w', encoding='utf-8-sig', newline='') as f:
            w = _csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            w.writeheader()
            for r in recs:
                w.writerow({k: _safe(v) for k, v in r.items()})
        print(json.dumps({'ok': True, 'out': str(out), 'rows': len(recs)},
                         ensure_ascii=False))
        return 0
    counts: dict[str, int] = {}
    for r in recs:
        counts[r['level']] = counts.get(r['level'], 0) + 1
        if args.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            print(f"{r['ts']} {r['level']:<5} {r['operation']:<9} "
                  f"{r['obj']} {r['result']}" +
                  (f" [{r['guid']}]" if r['guid'] else ''))
    print(json.dumps({'counts': counts, 'total': len(recs)},
                     ensure_ascii=False), file=sys.stderr)
    return 0


def cmd_audit_verify(args: argparse.Namespace) -> int:
    """Проверка tamper-evident цепочки журнала (Фаза 42)."""
    from .audit import verify_audit

    try:
        errs = verify_audit(args.audit_file, cross_files=args.cross_files)
    except (OSError, ValueError) as exc:
        return _err(f'audit-verify: {exc}')
    if errs:
        for e in errs:
            print(json.dumps(e, ensure_ascii=False))
        print(f'audit-verify: {len(errs)} нарушений', file=sys.stderr)
        return 1
    print('audit-verify: цепочка цела')
    return 0


# ---- Фаза 56: CLI-пайплайн migrate + wizard ----------------

def _extract_for_migrate(source_dir: str, encoding: str, specs: list[Any],
                         workers: int) -> list[dict[str, Any]]:
    """Извлечение объектов для migrate: оба формата 7.7/8.x."""
    ver = _detect_version(source_dir)
    if ver == '77':
        return _extract_77(source_dir, encoding, 0, specs)
    return _extract_8x(source_dir, 0, specs, workers=workers)


def cmd_migrate(args: argparse.Namespace) -> int:
    """Сквозной перенос одной командой (аудит раунда 6, C4):
    extract → transform (правила) → load (файл или --direct).
    В отличие от MCP migrate (HTTP), здесь любые источники 7.7/8.x и
    прямая запись в копию 1CD. Если --rules не задан — данные извлекаются
    и грузятся без трансформации."""
    from .config import ProjectConfig
    from .load_8x import LoadError, load_direct
    from .transform import TransformError, transform_object

    src = Path(args.source_dir)
    if not src.is_dir():
        return _err(f'источник не каталог: {args.source_dir}')
    cfg = ProjectConfig.load()
    encoding = args.source_encoding or cfg.source_encoding or 'cp866'
    t0 = time.perf_counter()
    try:
        objs = _extract_for_migrate(str(src), encoding, [], args.workers)
    except CLIError as exc:
        return _err(str(exc))
    if not objs:
        return _err('не извлечено ни одного объекта')
    _done_note(f'извлечено: {len(objs)} объектов', t0)

    if args.rules:
        try:
            rules = load_rules(args.rules)
        except MappingError as exc:
            return _err(f'migrate: правила: {exc}')
        rule_map = {r['source']: r for r in rules.get('objects', [])}
        out: list[dict[str, Any]] = []
        problems = 0
        for obj in objs:
            rule = rule_map.get(obj.get('type', ''))
            if rule is None:
                problems += 1
                continue
            try:
                out.append(transform_object(obj, rule, None, rules.get('enums')))  # type: ignore[arg-type]
            except TransformError:
                problems += 1
        objs = out
        _done_note(f'преобразовано: {len(objs)} объектов'
                   + (f' (без правила: {problems})' if problems else ''), t0)

    if args.direct:
        try:
            rep = load_direct(args.direct, objs, workdir=args.workdir or None,
                              snapshot=not args.no_snapshot)
        except LoadError as exc:
            return _err(f'migrate: запись: {exc}')
        print(json.dumps(rep, ensure_ascii=False, default=str))
        _done_note(f'загружено direct: {rep.get("total", 0)}', t0)
        return 0
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    save_json_batch(objs, target)
    print(json.dumps({'ok': True, 'objects': len(objs), 'file': str(target)},
                     ensure_ascii=False))
    _done_note(f'загружено в файл: {target}', t0)
    return 0


def cmd_wizard(args: argparse.Namespace) -> int:
    """Интерактивный мастер переноса (аудит раунда 6, G2): задаёт пару
    вопросов и собирает/запускает команду migrate, не заменяя
    низкоуровневые команды."""
    import shlex

    def ask(prompt: str, default: str = '') -> str:
        suff = f'  [{default}]' if default else ''
        try:
            v = input(f'{prompt}{suff}: ').strip()
        except EOFError:
            return ''
        return v or default

    print('onec-converter wizard — перенос между ИБ 1С\n')
    src = ask('Каталог источника (1Cv8.1CD / 1Cv7.dat)', os.getcwd())
    enc = ask('Кодировка источника (7.7: cp866/cp1251; 8.x: не важно)', 'cp866')
    rules = ask('Файл правил TOON rules.json (пусто — без трансформации)', '')
    direct = ask('Каталог приёмника для прямой записи 1CD (пусто — файл)', '')
    outp = ask('Файл промежуточного JSON', 'migrate-out.json')
    workers = ask('Потоков чтения для 8.x (1-8)', '2')

    argv = ['migrate', '--source-dir', src, '--source-encoding', enc,
            '--out', outp, '--workers', workers]
    if rules:
        argv += ['--rules', rules]
    if direct:
        argv += ['--direct', direct]
    print('\nВыполняю: onec-converter ' + ' '.join(shlex.quote(c) for c in argv))
    if getattr(args, 'no_run', False):
        print('(режим --no-run: команда не выполняется)')
        return 0
    return main(argv)


# ---- entry point ----

# Категории подкоманд для сгруппированного --help (аудит раунда 6, G1/G3/F4):
# помогает не теряться в 31 команде и отличать основные от операционных.
COMMAND_CATEGORIES: dict[str, str] = {
    # Разведка: понять что в базе
    'inspect': 'Разведка', 'stats': 'Разведка', 'query': 'Разведка',
    'dump-records': 'Разведка', 'export-xlsx': 'Разведка', 'shell': 'Разведка',
    'guid-diff': 'Разведка', 'config-versions': 'Разведка',
    # Перенос: полный цикл
    'extract': 'Перенос', 'map': 'Перенос', 'transform': 'Перенос',
    'load': 'Перенос', 'migrate': 'Перенос',
    'wizard': 'Перенос',
    # Проверка
    'verify': 'Проверка', 'rules-diff': 'Проверка', 'audit-verify': 'Проверка',
    'clone-db': 'Проверка',
    # Отчёты и аудит
    'audit': 'Отчёты и аудит', 'pii-report': 'Отчёты и аудит',
    'sonar-report': 'Отчёты и аудит', 'dump-report': 'Отчёты и аудит',
    'metrics': 'Отчёты и аудит',
    # Операционные: редко, для тех. интеграций
    'doctor': 'Служебные', 'cache': 'Служебные', 'techlog': 'Служебные',
    'fetch-config': 'Служебные', 'export-kd3': 'Служебные',
    'mint-token': 'Служебные', 'ai-map': 'Служебные',
    'ai-explain': 'Служебные', 'mcp': 'Служебные',
    'status': 'Служебные',
}


class _CategoryHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """help, где подкоманды сгруппированы по категориям."""

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            # собрать help каждого выбора из _choices_actions (argparse кладёт
            # help от add_parser(help=...) именно сюда, не в subparser)
            help_by: dict[str, str] = {}
            for ch in getattr(action, '_choices_actions', []):
                help_by[ch.dest] = ch.help or ''
            parts = ['', action.help or '', '']
            by_cat: dict[str, list[tuple[str, str]]] = {}
            for name in action.choices:
                cat = COMMAND_CATEGORIES.get(name, 'Прочее')
                by_cat.setdefault(cat, []).append((name, help_by.get(name, '')))
            order = ['Разведка', 'Перенос', 'Проверка', 'Отчёты и аудит',
                     'Служебные', 'Прочее']
            for cat in order:
                items = by_cat.pop(cat, [])
                if not items:
                    continue
                items.sort(key=lambda x: x[0])
                parts.append(f'  {cat}:')
                for name, h in items:
                    hl = self._format_text(h).strip() if h else ''
                    parts.append(f'    {name:<16} {hl}')
            return '\n'.join(parts) + '\n'
        return super()._format_action(action)


def _resolve_pretty(args: argparse.Namespace) -> bool:
    """Определить режим человек-читаемого вывода (аудит раунда 6, F1).

    --pretty/--no-pretty на root-парсере переопределяет авто-детект: включено,
    когда вывод идёт в TTY; при pipe/файле или --json выводим машиночитаемый
    JSON/CSV, чтобы не сломать скриптовую интеграцию."""
    from .terminal import is_tty

    flag = getattr(args, 'pretty', None)  # None = авто
    if flag is not None:
        return bool(flag)
    return is_tty()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='onec-converter',
        description='Перенос данных между ИБ 1С (CLI без MCP-клиента).',
        formatter_class=_CategoryHelpFormatter)  # ауд. раунда 6 G1: группы команд
    p.add_argument('--version', action='version',
                  version=__version__)
    p.add_argument('--pretty', dest='pretty', action='store_true', default=None,
                   help='человекочитаемый вывод (ASCII-таблица) — авто в TTY')
    p.add_argument('--no-pretty', dest='pretty', action='store_false',
                   help='машиночитаемый вывод (JSON/CSV) даже в TTY')
    sub = p.add_subparsers(dest='command', required=True)

    p_inspect = sub.add_parser('inspect', help='Метаданные источника')
    p_inspect.add_argument('--source-dir', required=True)
    p_inspect.add_argument('--source-encoding', default=DEFAULT_SOURCE_ENCODING)

    p_extract = sub.add_parser('extract', help='Извлечение данных в intermediate JSON')
    p_extract.add_argument('--source-dir', required=True)
    p_extract.add_argument('--source-encoding', default=DEFAULT_SOURCE_ENCODING)
    p_extract.add_argument('--out', required=True)
    p_extract.add_argument('--anonymize-fields', default='')
    p_extract.add_argument('--limit', type=int, default=0)
    p_extract.add_argument('--objects', default='',
                        help='селективный перенос (Фаза 29.2): CSV "Раздел.Имя" '
                             'или группы "Раздел.*" (Справочник.*/Документ.*/'
                             'Регистр.*), физические таблицы "Таблица._REFERENCE3"; '
                             'пусто — все данные')
    p_extract.add_argument('--audit-file', default='',
                           help='JSONL-журнал аудита переноса (Фаза 25)')
    p_extract.add_argument('--workers', type=int, default=1,
                           help='число потоков чтения (Фаза 34; 1 = последовательно)')
    p_extract.add_argument('--source-kind', default='1cd',
                           choices=['1cd', 'postgres', 'mssql'],
                           help='источник: файл 1CD или SQL-ИБ (Фаза 36)')
    p_extract.add_argument('--source-url', default='',
                           help='DSN/URL подключения к SQL-ИБ (при --source-kind)')
    p_extract.add_argument('--no-pii-masking', dest='pii_masking',
                           action='store_false', default=True,
                           help='не скрывать ПДн (ИНН/СНИЛС/тел) в журнале аудита '
                           '(по умолчанию маскируются, Фаза 42)')

    p_map = sub.add_parser('map', help='Правила маппинга (TOON)')
    p_map.add_argument('--rules-file', default='')
    p_map.add_argument('--init', action='store_true',
                       help='Шаблон правил из метаданных источника ('
                       'каждый объект -> та же таблица приёмника, Фаза 53 U12)')
    p_map.add_argument('--llm-prompt', action='store_true')
    p_map.add_argument('--meta-source', default='')
    p_map.add_argument('--meta-target', default='')
    p_map.add_argument('--out', default='')

    p_transform = sub.add_parser('transform', help='Применение правил к intermediate')
    p_transform.add_argument('--rules-file', required=True)
    p_transform.add_argument('--input', required=True)
    p_transform.add_argument('--out', default='')
    p_transform.add_argument('--preview', type=int, default=0)
    p_transform.add_argument('--audit-file', default='',
                             help='JSONL-журнал аудита переноса (Фаза 25)')
    p_transform.add_argument('--no-pii-masking', dest='pii_masking',
                             action='store_false', default=True,
                             help='не скрывать ПДн в журнале аудита (по умолчанию '
                             'маскируются, Фаза 42)')

    p_load = sub.add_parser('load', help='Загрузка в приёмник (файл/HTTP/прямая запись)')
    p_load.add_argument('--input', required=True)
    p_load.add_argument('--target', default='')
    p_load.add_argument('--http', default='')
    p_load.add_argument('--direct', default='',
                        help='каталог приёмника 8.x: запись в копию 1CD (Фаза 13)')
    p_load.add_argument('--workdir', default='',
                        help='каталог для копии приёмника (--direct)')
    p_load.add_argument('--notify-url', default='',
                        help='webhook URL по завершении (Фаза 27)')
    p_load.add_argument('--notify-telegram', default='',
                        help='token:chat_id Telegram по завершении (Фаза 27)')
    p_load.add_argument('--no-snapshot', action='store_true',
                        help='не сохранять snapshot.1CD приёмника до записи (Фаза 24)')
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
    p_load.add_argument('--secret', default='',
                        help='общий секрет для локального mint-token (HS256 JWT, Фаза 33)')
    p_load.add_argument('--index-repair', action='store_true',
                        help='сгенерировать скрипт восстановления индексов (--direct, Фаза 34)')
    p_load.add_argument('--no-pii-masking', dest='pii_masking',
                        action='store_false', default=True,
                        help='не скрывать ПДн в журнале аудита (по умолчанию '
                        'маскируются, Фаза 42)')
    p_load.add_argument('--dry-run', action='store_true',
                        help='демо-план без записи/отправки (Фаза 39)')
    p_load.add_argument('--retries', type=int, default=0,
                        help='число повторов HTTP (0 = из конфига/по умолчанию)')
    p_load.add_argument('--audit-file', default='',
                        help='JSONL-журнал аудита переноса (Фаза 25)')

    p_mig = sub.add_parser('migrate',
        help='Сквозной перенос одной командой (extract→transform→load, Фаза 56 C4)')
    p_mig.add_argument('--source-dir', required=True,
                       help='каталог источника (1Cv8.1CD или 1Cv7.MD/.dat)')
    p_mig.add_argument('--source-encoding', default='',
                       help='кодировка источника 7.7 (cp866/cp1251); пусто = из конфига')
    p_mig.add_argument('--rules', default='',
                       help='файл правил TOON rules.json (пусто — без трансформации)')
    p_mig.add_argument('--out', default='migrate-out.json',
                       help='промежуточный/результат JSON')
    p_mig.add_argument('--direct', default='',
                       help='каталог приёмника 1CD: прямая запись в копию')
    p_mig.add_argument('--workdir', default='', help='рабочий каталог копии (--direct)')
    p_mig.add_argument('--no-snapshot', action='store_true',
                       help='не сохранять snapshot приёмника (--direct)')
    p_mig.add_argument('--workers', type=int, default=2,
                       help='потоков чтения 8.x')

    p_wiz = sub.add_parser('wizard',
        help='Интерактивный мастер переноса (аудит раунда 6, G2)')
    p_wiz.add_argument('--no-run', action='store_true',
                       help='только напечатать команду, не выполнять')

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

    p_doc = sub.add_parser('doctor',
                           help='Диагностика окружения (Фаза 17/53): зависимости/кеш; --fix')
    p_doc.add_argument('--fix', action='store_true',
                       help='Починить поправимое (создать кеш) и показать команды '
                       'установки недостающих зависимостей (U13)')

    p_cache = sub.add_parser('cache', help='Кеш: stats / trim / clear (Фаза 18/48)')
    p_cache.add_argument('sub', nargs='?', default='stats',
                         choices=['stats', 'trim', 'clear'])
    p_cache.add_argument('--max-bytes', type=int, default=0,
                         help='trim: целевой лимит размера кеша в байтах')
    p_cache.add_argument('--ttl', type=int, default=0,
                         help='trim: удалять файлы старше N секунд')
    p_cache.add_argument('--root-dir', default='', help='Каталог кеша')

    p_dump = sub.add_parser('dump-records',
                            help='Первый N строк таблицы 1CD в JSON/CSV (Фаза 20)')
    p_dump.add_argument('--source-dir', required=True)
    p_dump.add_argument('--table', required=True)
    p_dump.add_argument('--limit', type=int, default=20)
    p_dump.add_argument('--format', choices=['json', 'csv'], default='json')
    p_dump.add_argument('--max-bytes', type=int, default=0,
                        help='Потоковый вывод: остановить после N байт (Фаза 49)')

    p_xlsx = sub.add_parser('export-xlsx',
                            help='Первые N строк таблицы 1CD в XLSX (Фаза 53 U11)')
    p_xlsx.add_argument('--source-dir', required=True)
    p_xlsx.add_argument('--table', required=True)
    p_xlsx.add_argument('--limit', type=int, default=1000)
    p_xlsx.add_argument('--out', default='', help='путь к .xlsx')

    p_stats = sub.add_parser('stats',
                             help='Сводка по ИБ 1CD: таблицы/строки/объём/locale (Фаза 53 U16)')
    p_stats.add_argument('--source-dir', required=True)

    p_mcp_g = sub.add_parser('mcp',
        help='MCP-сервер/тулы (Фаза 53 U15; --stdio запускает сервер, C1)')
    p_mcp_g.add_argument('--stdio', action='store_true',
                         help='запустить stdio-сервер (для MCP-клиентов)')
    p_mcp_g.add_argument('--sse', action='store_true',
                         help='запустить SSE-сервер (опционально)')

    sub.add_parser('metrics', help='Метрики в формате Prometheus (Фаза 21)')

    p_clone = sub.add_parser('clone-db',
                             help='Полная копия файловой ИБ в новый каталог (Фаза 24)')
    p_clone.add_argument('--source-dir', required=True,
                         help='каталог оригинала с 1Cv8.1CD (read-only)')
    p_clone.add_argument('--target-dir', required=True,
                         help='каталог копии (создаётся)')
    p_clone.add_argument('--with-rules', default='',
                         help='скопировать файл правил маппинга рядом (стенд)')

    p_audit = sub.add_parser('audit', help='Просмотр/фильтр журнала аудита (Фаза 25)')
    p_audit.add_argument('--file', required=True, help='JSONL-журнал (audit.jsonl)')
    p_audit.add_argument('--level', default='', help='INFO|WARN|ERROR')
    p_audit.add_argument('--op', default='', help='extract|transform|load')
    p_audit.add_argument('--obj', default='', help='подстрока имени объекта')
    p_audit.add_argument('--tail', type=int, default=0, help='последние N записей')
    p_audit.add_argument('--csv-out', default='',
                         help='выгрузка фильтра в CSV (комплаенс, Фаза 48)')

    p_av = sub.add_parser('audit-verify',
                          help='Проверка tamper-evident цепочки журнала (Фаза 42)')
    p_av.add_argument('--audit-file', required=True, help='JSONL-журнал')
    p_av.add_argument('--cross-files', action='store_true',
                      help='сверять границы с архивами ротации (.1/.2/...)')
    p_audit.add_argument('--json', action='store_true', help='полные JSON-записи')

    p_tl = sub.add_parser('techlog',
                          help='Техжурнал 1С как источник событий (Фаза 26)')
    p_tl.add_argument('--source-dir', required=True,
                      help='каталог техжурнала (файлы *.log/*.lgp)')
    p_tl.add_argument('--process', default='', help='процесс: rphost/rmngr/1CV8')
    p_tl.add_argument('--event', default='', help='событие: SDBL/EXCP/TTIMEOUT')
    p_tl.add_argument('--level-min', type=int, default=0,
                      help='уровень события >= (0..5)')
    p_tl.add_argument('--tail', type=int, default=0, help='последние N событий')
    p_tl.add_argument('--out', default='', help='запись JSON-файл')

    p_fc = sub.add_parser('fetch-config',
                          help='Релиз конфигурации (XML-выгрузка) как источник'
                               ' метаданных (Фаза 26)')
    p_fc.add_argument('--source', required=True,
                      help='каталог XML-выгрузки (Configuration.xml)')
    p_fc.add_argument('--out', default='', help='запись JSON-файл')

    p_dr = sub.add_parser('dump-report',
                          help='Экспорт отчёта (JSON/XLSX) в S3 (Фаза 27)')
    p_dr.add_argument('--file', required=True, help='файл отчёта')
    p_dr.add_argument('--s3', required=True, help='bucket')
    p_dr.add_argument('--endpoint', default='',
                      help='кастомный endpoint (MinIO/Yandex); пусто — AWS')
    p_dr.add_argument('--key', default='', help='access key (или AWS_* env)')
    p_dr.add_argument('--secret', default='', help='secret key (или AWS_* env)')
    p_dr.add_argument('--region', default='us-east-1', help='регион')

    p_sr = sub.add_parser('sonar-report',
                          help='Отчёт ruff в sonar-формате для CI (Фаза 28)')
    p_sr.add_argument('--target', default='src',
                      help='каталог/файл линтинга (по умолчанию src)')
    p_sr.add_argument('--format', default='xml', choices=('xml', 'json'),
                      help='xml — Generic Issue Import (по умолчанию); json')
    p_sr.add_argument('--out', default='',
                      help='запись отчёта в файл (иначе stdout)')

    p_kd3 = sub.add_parser('export-kd3',
                           help='Экспорт правил TOON в XML в стиле КД3 (Фаза 29.2)')
    p_kd3.add_argument('--rules', required=True, help='файл правил rules.json')
    p_kd3.add_argument('--out', default='', help='запись XML-файла')

    p_mint = sub.add_parser('mint-token',
                            help='Выпуск локального JWT Bearer-токена (Фаза 33)')
    p_mint.add_argument('--secret', required=True,
                        help='общий секрет приёмника (как в Module.bsl ОжидаемыйКлюч)')
    p_mint.add_argument('--issuer', default='onec-converter',
                        help='issuer токена')
    p_mint.add_argument('--exp-min', type=int, default=60,
                        help='срок жизни в минутах')
    p_mint.add_argument('--kid', default='',
                        help='id ключа для ротации JWT (в header токена, U30;'
                        ' приёмник выбирает секрет по kid из НаборСекретовJWT)')
    p_mint.add_argument('--dry-run', action='store_true',
                        help='показать header/payload без подписи (Фаза 45)')
    p_mint.add_argument('--json', action='store_true',
                        help='вывод {"token","exp"} для скриптов (Фаза 45)')

    p_am = sub.add_parser('ai-map',
                          help='Авто-маппинг схем двух баз -> правила TOON (Фаза 45)')
    p_am.add_argument('--source-dir', required=True, help='ИБ-источник')
    p_am.add_argument('--target-dir', required=True, help='ИБ-приёмник')
    p_am.add_argument('--objects', default='',
                      help='Фильтр объектов (см. extract --objects, Фаза 51 U25)')
    p_am.add_argument('--out', default='',
                      help='запись правил rules.json (иначе stdout)')

    p_ae = sub.add_parser('ai-explain',
                          help='Причины расхождений структур двух баз (Фаза 45)')
    p_ae.add_argument('--source-dir', required=True, help='ИБ-источник')
    p_ae.add_argument('--target-dir', required=True, help='ИБ-приёмник')

    p_v = sub.add_parser('verify',
                         help='Сверка источник↔приёмник (Фаза 48)')
    p_v.add_argument('--input', required=True,
                     help='объекты источника (intermediate JSON)')
    p_v.add_argument('--target', required=True,
                     help='объекты приёмника (intermediate JSON после load)')
    p_v.add_argument('--objects', default='',
                     help='фильтр по типу/группе (как в extract)')
    p_v.add_argument('--json', action='store_true',
                     help='машиночитаемый отчёт для CI')

    p_rd = sub.add_parser('rules-diff',
                          help='Сравнение двух правил TOON (Фаза 48)')
    p_rd.add_argument('--a', required=True, help='правила v1 (rules.json)')
    p_rd.add_argument('--b', required=True, help='правила v2 (rules.json)')
    p_rd.add_argument('--json', action='store_true', help='JSON-отчёт')

    p_pii = sub.add_parser('pii-report',
                           help='Отчёт по анонимизации ПДн (152-ФЗ/152 УЗ, Фаза 37)')
    p_pii.add_argument('--audit-file', required=True,
                       help='JSONL-журнал аудита')
    p_pii.add_argument('--rules-file', default='',
                       help='файл правил TOON (для перечня полей)')
    p_pii.add_argument('--profile', default='RU', choices=['RU', 'UZ'],
                       help='профиль ПДн (RU/152-ФЗ или UZ/152 УЗ)')

    p_shell = sub.add_parser('shell',
                             help='Интерактивная оболочка исследования базы (Фаза 39)')
    p_shell.add_argument('--source-dir', required=True,
                         help='каталог с 1Cv8.1CD')

    return p


def main(argv: list[str] | None = None) -> int:
    # Надёжность консоли (аудит раунда 6, H-fix): на Windows cp1251-консолях
    # help и вывод с кириллицей/спецсимволами (↔ …) падали UnicodeEncodeError.
    # Переключаем stdout/stderr на UTF-8 с errors='replace' — CLI не падает
    # ни на какой кодовой странице, а непечатные байты не роняют процесс.
    for _s in (sys.stdout, sys.stderr):
        reconfigure = getattr(_s, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass  # не-файловый поток — трогать нечего
    args = build_parser().parse_args(argv)
    # аудит (Фаза 25): файл из --audit-file или ONEC_AUDIT_FILE (для MCP)
    audit_file = getattr(args, 'audit_file', '') or os.environ.get('ONEC_AUDIT_FILE', '')
    if audit_file:
        set_audit(audit_file, pii_masking=getattr(args, 'pii_masking', True))
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
        'clone-db': cmd_clone_db,
        'audit': cmd_audit,
        'audit-verify': cmd_audit_verify,
        'techlog': cmd_techlog,
        'fetch-config': cmd_fetch_config,
        'dump-report': cmd_dump_report,
        'sonar-report': cmd_sonar_report,
        'export-kd3': cmd_export_kd3,
        'mint-token': cmd_mint_token,
        'ai-map': cmd_ai_map,
        'ai-explain': cmd_ai_explain,
        'verify': cmd_verify,
        'rules-diff': cmd_rules_diff,
        'pii-report': cmd_pii_report,
        'export-xlsx': cmd_export_xlsx,
        'stats': cmd_stats,
        'mcp': cmd_mcp,
        'migrate': cmd_migrate,
        'wizard': cmd_wizard,
        'shell': cmd_shell,
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
