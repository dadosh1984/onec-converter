"""Сквозной перенос через SQLite: общая функция (CLI + скрипт)."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import onec_converter.sqlite_com_load as sqlite_com_load

from .cache import Cache, file_key
from .classify import build_plan
from .index_rebuilder import build_repair_script
from .source_8x_file import read_metadata
from .sqlite_automap import auto_map_sqlite
from .sqlite_extract import extract_to_sqlite
from .sqlite_load import load_from_sqlite
from .sqlite_transform import apply_mapping
from .validate_transfer import validate_migration

# Объекты, исключённые из переноса (не копируются в приёмник)
EXCLUDED_OBJECTS: set[str] = {
    'Справочник.Банки',
    'Справочник.Валюты',
}

# Префиксы объектов приёмника, которые не используем как цель переноса
EXCLUDED_TARGET_PREFIXES: tuple[str, ...] = (
    'uzbled_', 'dibank_', 'eaktiv_', 'aslbelgisi_',
)
from .bridge_format import MODE_CATALOG, MODE_REGISTER
from .cache import Cache, file_key
from .index_rebuilder import build_repair_script


def _extract_cached(cd_path: Path, sqlite_out: Path, limit: int,
                    cache_dir: str | None, no_cache: bool) -> bool:
    """Выгрузка с кешированием. True = cache hit. ponytail: rung 2 — cache.py."""
    if no_cache or cache_dir is None:
        extract_to_sqlite(cd_path.parent, sqlite_out, limit=limit)
        return False

    cache = Cache(root=Path(cache_dir))
    key = file_key(cd_path)
    if cache.has(key, 'extract.sqlite'):
        cached = cache.get(key, 'extract.sqlite')
        shutil.copy2(str(cached), str(sqlite_out))
        return True

    extract_to_sqlite(cd_path.parent, sqlite_out, limit=limit)
    cache.put(key, 'extract.sqlite', sqlite_out.read_bytes())
    return False


def _generate_index_script(workdir: Path) -> Path | None:
    """Сгенерировать скрипт восстановления индексов. ponytail: rung 2 — index_rebuilder."""
    try:
        result = build_repair_script(str(workdir), tool='auto')
        if result.get('ok') and result.get('script'):
            return Path(result['script'])
    except Exception:
        pass  # ponytail: не ронять миграцию если нет 1cv8/chdbfl
    return None


def _safe_xlsx_name(name: str) -> str:
    """Безопасное имя файла из имени объекта. ponytail: rung 3 — str.replace."""
    return name.replace('.', '_').replace('/', '_')[:64]


def _copy_object_mapping(src_path: Path, tgt_path: Path) -> None:
    """Скопировать _object_mapping из source в target. ponytail: rung 2."""
    src_con = sqlite3.connect(str(src_path))
    has = src_con.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='_object_mapping'"
    ).fetchone()[0]
    if not has:
        src_con.close()
        return
    tgt_con = sqlite3.connect(str(tgt_path))
    tgt_con.execute('DROP TABLE IF EXISTS _object_mapping')
    rows = src_con.execute('SELECT * FROM _object_mapping').fetchall()
    if rows:
        cols = [d[1] for d in src_con.execute('PRAGMA table_info(_object_mapping)')]
        col_str = ', '.join(cols)
        ph = ', '.join(['?'] * len(cols))
        tgt_con.execute(f'CREATE TABLE _object_mapping ({col_str})')
        tgt_con.executemany(f'INSERT INTO _object_mapping VALUES ({ph})', rows)
    tgt_con.commit()
    tgt_con.close()
    src_con.close()


def _copy_field_mapping(src_path: Path, tgt_path: Path) -> None:
    """Скопировать _field_mapping из source в target. ponytail: rung 2."""
    src_con = sqlite3.connect(str(src_path))
    has = src_con.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='_field_mapping'"
    ).fetchone()[0]
    if not has:
        src_con.close()
        return
    tgt_con = sqlite3.connect(str(tgt_path))
    tgt_con.execute('DROP TABLE IF EXISTS _field_mapping')
    rows = src_con.execute('SELECT * FROM _field_mapping').fetchall()
    if rows:
        cols = [d[1] for d in src_con.execute('PRAGMA table_info(_field_mapping)')]
        col_str = ', '.join(cols)
        ph = ', '.join(['?'] * len(cols))
        tgt_con.execute(f'CREATE TABLE _field_mapping ({col_str})')
        tgt_con.executemany(f'INSERT INTO _field_mapping VALUES ({ph})', rows)
    tgt_con.commit()
    tgt_con.close()
    src_con.close()


def _run_chdbfl(db_path: Path) -> None:
    """Запустить chdbfl для пересборки индексов. ponytail: rung 4 — native tool."""
    import subprocess
    candidates = [
        Path(r'C:/Program Files/1cv8/8.3.27.2074/bin/chdbfl.exe'),
        Path(r'C:/Program Files (x86)/1cv8/8.3.27.2074/bin/chdbfl.exe'),
    ]
    for chdbfl in candidates:
        if chdbfl.is_file():
            try:
                subprocess.run([str(chdbfl), str(db_path)], capture_output=True, timeout=120)
                return
            except Exception:
                pass


def run_migrate_all_full(
    source_dir: str | Path,
    target_dir: str | Path,
    sqlite_path: str | Path,
    report_path: str | Path,
    workdir: str | Path | None = None,
    limit: int = 0,
    cache_dir: str | None = None,
    no_cache: bool = False,
    source_encoding: str = '',
) -> dict[str, Any]:
    """Полный цикл с авто-маппингом: extract→extract→automap→apply→load."""
    src = Path(source_dir)
    dst = Path(target_dir)
    src_cd = src / '1Cv8.1CD'
    dst_cd = dst / '1Cv8.1CD'

    if not src_cd.is_file():
        return {'ok': False, 'error': f'нет файла источника: {src_cd}'}
    if not dst_cd.is_file():
        return {'ok': False, 'error': f'нет файла приёмника: {dst_cd}'}

    sqlite_file = Path(sqlite_path)
    report_file = Path(report_path)
    sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    sqlite_src = sqlite_file.parent / f'{sqlite_file.stem}_src{sqlite_file.suffix}'
    sqlite_tgt = sqlite_file.parent / f'{sqlite_file.stem}_tgt{sqlite_file.suffix}'
    for f in (sqlite_src, sqlite_tgt, sqlite_file):
        if f.exists():
            f.unlink()

    # 1. Extract с кешем
    cache_hit_src = _extract_cached(src_cd, sqlite_src, limit, cache_dir, no_cache)
    cache_hit_dst = _extract_cached(dst_cd, sqlite_tgt, limit, cache_dir, no_cache)

    # 2. Auto-map
    # Сначала фильтруем приёмник — убираем объекты с нежелательными префиксами
    tgt_con = sqlite3.connect(str(sqlite_tgt))
    for prefix in EXCLUDED_TARGET_PREFIXES:
        tgt_con.execute(
            "UPDATE _objects SET category='skip' WHERE name LIKE ?",
            [f'%.{prefix}%'])
    tgt_con.commit()
    tgt_con.close()

    mp = auto_map_sqlite(str(sqlite_src), str(sqlite_tgt))

    # Исключаем объекты: чёрный список + префиксы приёмника
    ex_con = sqlite3.connect(str(sqlite_src))
    has_om = ex_con.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='_object_mapping'"
    ).fetchone()[0]
    if has_om:
        if EXCLUDED_OBJECTS:
            placeholders = ', '.join(['?'] * len(EXCLUDED_OBJECTS))
            ex_con.execute(
                f'UPDATE _object_mapping SET status=? '
                f'WHERE source_name IN ({placeholders})',
                ['skip'] + list(EXCLUDED_OBJECTS))
        # Объекты приёмника с нежелательными префиксами — пропускаем
        for prefix in EXCLUDED_TARGET_PREFIXES:
            ex_con.execute(
                "UPDATE _object_mapping SET status='skip' "
                "WHERE target_name LIKE ? AND status='ready'",
                [f'%.{prefix}%'])
        ex_con.commit()
    ex_con.close()

    # 3. Apply
    applied = apply_mapping(str(sqlite_src), str(sqlite_tgt))

    # Копируем _object_mapping + _field_mapping в target (нужно для load_via_com)
    _copy_object_mapping(sqlite_src, sqlite_tgt)
    _copy_field_mapping(sqlite_src, sqlite_tgt)

    if sqlite_file.exists():
        sqlite_file.unlink()
    shutil.copy2(str(sqlite_tgt), str(sqlite_file))

    # 4. Load через COM/объектную модель
    wd = Path(workdir) if workdir else Path(src).parent / 'tmp' / 'migrate_full_work'
    wd.mkdir(parents=True, exist_ok=True)
    work_copy = wd / '1Cv8.1CD'
    if work_copy.exists():
        work_copy.unlink()
    shutil.copy2(str(dst_cd), str(work_copy))

    loaded = sqlite_com_load.load_via_com(str(sqlite_tgt), str(wd))
    result_copy = work_copy
    # Запускаем chdbfl для пересборки индексов
    _run_chdbfl(result_copy)

    # 5. Валидация результата
    validation = validate_migration(
        str(sqlite_tgt),
        source_sqlite=str(sqlite_src) if sqlite_src.exists() else None)

    # 6. Индексы
    index_script = _generate_index_script(wd)

    report = {
        'ok': True,
        'auto_map': mp,
        'apply': applied,
        'load': loaded,
        'validation': {
            'errors': validation.total_errors,
            'warnings': validation.total_warnings,
            'ok': validation.ok,
        },
        'report_path': str(report_file),
        'work_copy': str(result_copy),
        'total_created': loaded.get('created', loaded.get('rows_written', 0)),
        'cache_hit': cache_hit_src or cache_hit_dst,
        'index_script': str(index_script) if index_script else None,
    }
    report_file.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, report_file.open('w', encoding='utf-8'), ensure_ascii=False, indent=2, default=str)

    return report


def run_migrate_all(
    source_dir: str | Path,
    target_dir: str | Path,
    sqlite_path: str | Path,
    report_path: str | Path,
    workdir: str | Path | None = None,
    limit: int = 0,
    cache_dir: str | None = None,
    no_cache: bool = False,
    source_encoding: str = '',
) -> dict[str, Any]:
    """Перенос всех user-данных 1С 8.x через SQLite."""
    src = Path(source_dir)
    dst = Path(target_dir)
    src_cd = src / '1Cv8.1CD'
    src_md = src / '1Cv7.MD'
    dst_cd = dst / '1Cv8.1CD'

    is_77 = src_md.is_file() and not src_cd.is_file()
    if not is_77 and not src_cd.is_file():
        return {'ok': False, 'error': f'нет файла источника: {src_cd} (ни 8.x, ни 7.7)'}
    if not dst_cd.is_file():
        return {'ok': False, 'error': f'нет файла приёмника: {dst_cd}'}

    sqlite_file = Path(sqlite_path)
    report_file = Path(report_path)

    # Рабочий каталог (общий для 7.7 и 8.x)
    wd = Path(workdir) if workdir else Path(src).parent / 'tmp' / 'migrate_work'
    wd.mkdir(parents=True, exist_ok=True)

    # План и выгрузка
    if is_77:
        from .v77_sqlite_extract import v77_extract_to_sqlite
        enc = source_encoding or 'cp866'
        v77_extract_to_sqlite(src, sqlite_file, encoding=enc)
        # Для 7.7 план — все user-объекты из SQLite
        con = sqlite3.connect(str(sqlite_file))
        user_plan_rows = con.execute(
            "SELECT name, kind FROM _objects WHERE category='user'").fetchall()
        con.close()
        user_plan = [{'name': r[0], 'kind': r[1]} for r in user_plan_rows]
        # Исключаем объекты из чёрного списка
        user_plan = [p for p in user_plan if p['name'] not in EXCLUDED_OBJECTS]
        cache_hit = False
    else:
        md_src = read_metadata(str(src_cd))
        md_dst = read_metadata(str(dst_cd))
        plan = build_plan(md_src)
        dst_objects = {f"{o['kind']}.{o['name']}" for o in md_dst.get('objects', [])}
        user_plan = [p for p in plan if p['category'] == 'user' and p['name'] in dst_objects]
        # Исключаем объекты из чёрного списка
        user_plan = [p for p in user_plan if p['name'] not in EXCLUDED_OBJECTS]
        cache_hit = _extract_cached(src_cd, sqlite_file, limit, cache_dir, no_cache)

    # _object_mapping: для 7.7 создаём вручную, для 8.x — через auto_map_sqlite
    if is_77:
        con = sqlite3.connect(str(sqlite_file))
        con.execute('DROP TABLE IF EXISTS _object_mapping')
        con.execute('''CREATE TABLE _object_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL, target_name TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'ready',
            note TEXT DEFAULT ''
        )''')
        plan_rows = [(p['name'], p['name'], p.get('kind', '')) for p in user_plan]
        con.executemany(
            'INSERT INTO _object_mapping (source_name, target_name, source_kind, status) VALUES (?, ?, ?, ?)',
            [(r[0], r[1], r[2], 'ready') for r in plan_rows])
        con.commit()
        con.close()

    if is_77:
        # 7.7: отдельный путь (нет COM-маппинга, только прямая запись)
        return _run_migrate_77(src, dst, sqlite_file, report_file, wd, limit,
                               source_encoding, cache_hit)

    # 8.x: используем run_migrate_all_full (COM-путь, проверенный)
    # ponytail: rung 2 — run_migrate_all_full уже работает и протестирован
    return run_migrate_all_full(
        source_dir=str(src), target_dir=str(dst),
        sqlite_path=str(sqlite_file), report_path=str(report_file),
        workdir=str(wd), limit=limit, cache_dir=cache_dir, no_cache=no_cache,
        source_encoding=source_encoding)


def _run_migrate_77(src: Path, dst: Path, sqlite_file: Path, report_file: Path,
                    wd: Path, limit: int, source_encoding: str,
                    cache_hit: bool) -> dict[str, Any]:
    """Перенос 7.7 → 8.x: только прямая запись (нет COM)."""
    dst_cd = dst / '1Cv8.1CD'
    work_copy = wd / '1Cv8.1CD'
    if work_copy.exists():
        work_copy.unlink()
    shutil.copy2(str(dst_cd), str(work_copy))

    result = load_from_sqlite(str(sqlite_file), str(wd), workdir=str(wd),
                              max_objects=limit if limit else 0)
    result_copy = Path(result.get('work_copy', str(wd / 'work.1CD')))
    if not result_copy.exists():
        result_copy = wd / '1Cv8.1CD'
    _run_chdbfl(result_copy)

    index_script = _generate_index_script(wd)

    report: dict[str, Any] = {
        'ok': [], 'errors': [],
        'total_created': 0, 'total_updated': 0, 'total_skipped': 0,
    }
    for obj in result.get('objects', []):
        if 'error' in obj:
            report['errors'].append({'obj': obj.get('source', '?'),
                                     'stage': 'import', 'error': obj['error']})
        else:
            rows = obj.get('rows', 0)
            report['ok'].append({'obj': obj.get('source', obj.get('target', '?')),
                                 'created': rows, 'updated': 0, 'skipped': 0})
            report['total_created'] += rows

    report_file.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, report_file.open('w', encoding='utf-8'), ensure_ascii=False, indent=2)

    return {
        'ok': True,
        'objects': result.get('objects', []),
        'total_created': report['total_created'],
        'report_path': str(report_file),
        'work_copy': str(result_copy),
        'cache_hit': cache_hit,
        'index_script': str(index_script) if index_script else None,
    }
