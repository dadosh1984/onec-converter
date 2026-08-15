"""Загрузка данных из SQLite в копию 1CD приёмника — прямая запись.

Одна копия базы, все объекты пачкой, без промежуточных xlsx.
Использует append_records из write_8x и кодировщики из fake_1cd/load_8x_refs.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import struct
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .epf_load import BridgeError
from .fake_1cd import enc_datetime, enc_nc, enc_numeric, enc_nvc
from .source_8x_file import Database1CD, read_metadata
from .write_8x import append_records, copy_1cd


def load_from_sqlite(sqlite_path: str | Path,
                     target_dir: str | Path,
                     workdir: str | Path | None = None,
                     max_objects: int = 0) -> dict[str, Any]:
    """Загрузить данные из SQLite напрямую в копию 1CD (одна копия, все объекты).

    Args:
        sqlite_path: путь к .sqlite (target.sqlite после apply_mapping)
        target_dir: каталог приёмника с оригиналом 1Cv8.1CD
        workdir: рабочий каталог (None = E:/tmp)
        max_objects: лимит объектов (0 = все)

    Returns:
        {'ok': True/False, 'total': N, 'rows_written': N, 'objects': [...]}
    """
    src = Path(sqlite_path)
    target = Path(target_dir)
    cd = target / '1Cv8.1CD'
    if not cd.is_file():
        raise FileNotFoundError(f'нет: {cd}')

    # ponytail: TEMP на E:, не на C:
    _tmp_base = Path(os.environ.get('ONEC_TEST_TMP', 'E:/tmp'))
    wd = Path(workdir) if workdir else Path(
        tempfile.mkdtemp(prefix='onec_direct_', dir=str(_tmp_base)))
    wd.mkdir(parents=True, exist_ok=True)

    # ОДНА копия
    work = wd / 'work.1CD'
    copy_1cd(cd, work)

    con = sqlite3.connect(str(src))
    con.row_factory = sqlite3.Row

    # ready-объекты — через _object_mapping, если есть
    has_mapping = con.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='_object_mapping'"
    ).fetchone()[0]

    if has_mapping:
        mappings = con.execute(
            "SELECT id, source_name, target_name, source_kind "
            "FROM _object_mapping WHERE status='ready' "
            "ORDER BY CASE WHEN source_kind='Справочник' THEN 1 "
            "WHEN source_kind='Документ' THEN 2 ELSE 3 END"
        ).fetchall()
    else:
        # без маппинга — все user-объекты как есть
        mappings = con.execute(
            "SELECT id, name AS source_name, name AS target_name, kind AS source_kind "
            "FROM _objects WHERE category='user' "
            "ORDER BY CASE WHEN kind='Справочник' THEN 1 "
            "WHEN kind='Документ' THEN 2 ELSE 3 END"
        ).fetchall()

    if max_objects and len(mappings) > max_objects:
        mappings = mappings[:max_objects]

    if not mappings:
        con.close()
        return {'ok': True, 'total': 0, 'rows_written': 0, 'objects': []}

    # метаданные приёмника для маппинга field→FieldDef
    md = read_metadata(work)
    obj_index = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}

    report_objects: list[dict[str, Any]] = []
    total_rows = 0

    for om_id, src_name, tgt_name, src_kind in mappings:
        # ищем объект приёмника
        tgt_obj = obj_index.get(tgt_name)
        if tgt_obj is None:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': f'объект {tgt_name!r} не найден в приёмнике',
            })
            continue

        table_name = tgt_obj.get('table', '')
        if not table_name:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': 'нет table_name в метаданных',
            })
            continue

        # читаем данные из SQLite
        try:
            rows = con.execute(f'SELECT * FROM [{src_name}]').fetchall()
        except sqlite3.OperationalError:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': f'нет таблицы {src_name!r} в sqlite',
            })
            continue

        if not rows:
            continue

        # кодируем строки
        raw_rows = _encode_rows(work, table_name, rows)
        if not raw_rows:
            continue

        try:
            written = append_records(work, table_name, raw_rows)
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': len(rows), 'bytes_written': written,
            })
            total_rows += len(rows)
        except Exception as e:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': str(e),
            })

    con.close()

    # ponytail: результат — копия с дописанными данными
    return {
        'ok': True,
        'total': len(report_objects),
        'rows_written': total_rows,
        'objects': report_objects,
        'work_copy': str(work),
    }


def _encode_rows(work_path: Path, table_name: str,
                 rows: list[sqlite3.Row]) -> bytes:
    """Закодировать строки в сырой формат 1CD."""
    with Database1CD(work_path) as db:
        if table_name not in db.tables:
            return b''
        t = db.tables[table_name]
        rl = t.row_length

        result = bytearray()
        for row in rows:
            buf = bytearray(rl)

            # _IDRREF — генерируем новый GUID
            idr = t.fields.get('_IDRREF')
            if idr is not None:
                new_guid = uuid.uuid4().bytes  # 16 случайных байт
                buf[idr.offset:idr.offset + 16] = new_guid

            # кодируем поля
            for fname, fdef in t.fields.items():
                if fname == '_IDRREF':
                    continue
                if fname in ('_VERSION', '_MARKED', '_ISMETADATA',
                             '_FOLDER', '_ORDERFIELD', '_KIND'):
                    continue

                # значение из sqlite-строки — по имени поля
                val = _get_row_value(row, fname)
                if val is not None:
                    _encode_field_safe(buf, fdef, val)

            result.extend(buf)

        return bytes(result)


def _get_row_value(row: sqlite3.Row, field_name: str) -> Any:
    """Получить значение из Row по физическому имени поля."""
    try:
        return row[field_name]
    except (IndexError, KeyError):
        return None


def _encode_field_safe(buf: bytearray, fdef: Any, value: Any) -> None:
    """Закодировать значение, игнорируя ошибки."""
    try:
        ft = fdef.type
        if ft == 'NVC':
            raw = enc_nvc(str(value) if value else '', fdef.length,
                          fdef.null_exists)
            buf[fdef.offset:fdef.offset + len(raw)] = raw
        elif ft == 'NC':
            raw = enc_nc(str(value) if value else '', fdef.length)
            buf[fdef.offset:fdef.offset + len(raw)] = raw
        elif ft == 'N':
            try:
                raw = enc_numeric(float(value), fdef.length, fdef.precision)
                buf[fdef.offset:fdef.offset + len(raw)] = raw
            except (ValueError, TypeError):
                pass
        elif ft == 'L':
            buf[fdef.offset] = 1 if value else 0
        elif ft == 'DT':
            if value:
                raw = enc_datetime(str(value))
                buf[fdef.offset:fdef.offset + len(raw)] = raw
        elif ft in ('B', 'RV') and isinstance(value, str) and len(value) == 36:
            # GUID-строка → 16 байт
            raw = bytes.fromhex(value.replace('-', ''))
            if len(raw) == 16:
                buf[fdef.offset:fdef.offset + 16] = raw
    except Exception:
        pass  # ponytail: битые поля не должны ронять весь перенос
