"""Выгрузка всех пользовательских данных из файловой ИБ 1С 8.x в SQLite.

Один проход Database1CD → все user-таблицы в .sqlite. Без внешних зависимостей
(sqlite3 из stdlib). WAL-режим, пакетная вставка (executemany).
"""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any

from .classify import classify_objects
from .source_8x_file import Database1CD, bin_to_guid, decode_field, read_metadata


def extract_to_sqlite(source_dir: str | Path, output_path: str | Path,
                      limit: int = 0) -> Path:
    """Выгрузить все user-таблицы из 1CD в SQLite за один проход.

    Args:
        source_dir: путь к каталогу с 1Cv8.1CD
        output_path: путь к создаваемому .sqlite
        limit: если >0 — макс. число строк на таблицу (для тестов)

    Returns:
        Path к созданному файлу
    """
    source = Path(source_dir)
    cd_path = source / '1Cv8.1CD'
    if not cd_path.is_file():
        raise FileNotFoundError(f'нет файла: {cd_path}')

    md = read_metadata(str(cd_path))
    classified = classify_objects(md)
    objects: list[dict[str, Any]] = []
    for obj in md.get('objects', []):
        full = f"{obj['kind']}.{obj['name']}"
        obj['_full'] = full
        obj['_category'] = classified.get(full, 'service')
        objects.append(obj)

    out = Path(output_path)
    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(out))
    # адаптер datetime → ISO-8601 (без deprecation warning Python 3.12+)
    def _adapt_dt(val: datetime.datetime) -> str:
        return val.isoformat(sep=' ')
    sqlite3.register_adapter(datetime.datetime, _adapt_dt)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')

    _create_meta_tables(con)
    _insert_objects(con, objects)
    _insert_columns(con, objects)

    if limit is None:
        limit = 0
    if limit >= 0:
        _extract_data(con, cd_path, objects, classified, limit)

    con.commit()
    con.close()
    return out


def _create_meta_tables(con: sqlite3.Connection) -> None:
    con.execute('''CREATE TABLE _objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        synonym TEXT DEFAULT '',
        table_name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'user',
        row_count INTEGER DEFAULT 0
    )''')
    con.execute('''CREATE TABLE _columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER NOT NULL REFERENCES _objects(id),
        col_name TEXT NOT NULL,
        field_name TEXT NOT NULL,
        type TEXT NOT NULL,
        length INTEGER DEFAULT 0,
        precision INTEGER DEFAULT 0
    )''')


def _insert_objects(con: sqlite3.Connection,
                    objects: list[dict[str, Any]]) -> None:
    rows: list[tuple[str, str, str, str, str]] = []
    for obj in objects:
        rows.append((obj['kind'], obj['_full'], obj.get('synonym', ''),
                     obj.get('table', ''), obj['_category']))
    con.executemany(
        'INSERT INTO _objects (kind, name, synonym, table_name, category) '
        'VALUES (?, ?, ?, ?, ?)', rows)


def _insert_columns(con: sqlite3.Connection,
                    objects: list[dict[str, Any]]) -> None:
    """Заполняется позже в _extract_data — здесь только структура."""
    # noop: _extract_data заполнит _columns теми же полями что и таблицы данных
    pass


# поля, исключаемые из выгрузки данных
_SKIP_FIELDS = {
    '_VERSION', '_MARKED', '_ISMETADATA', '_FOLDER',
    '_ORDERFIELD', '_PREDEFINEDID', '_PARENTIDRREF', '_OWNERIDRREF',
    '_RECORDER', '_LINENO', '_KIND', '_NEWREF', '_NUMBERPREFIX',
}
# поля, которые выгружаем всегда (нужны для ссылочной целостности)
_KEEP_FIELDS = {'_IDRREF', '_DATE_TIME'}


def _extract_data(con: sqlite3.Connection, cd_path: Path,
                  objects: list[dict[str, Any]],
                  classified: dict[str, str],
                  limit: int = 0) -> None:
    """Один проход Database1CD: для каждого user-объекта — CREATE TABLE + INSERT."""
    with Database1CD(cd_path) as db:
        for obj in objects:
            if obj['_category'] != 'user':
                continue
            table_name = obj.get('table', '')
            if not table_name or table_name not in db.tables:
                continue

            tdef = db.tables[table_name]
            # выбрать поля для выгрузки: не служебные + _IDRREF и _DATE_TIME
            fields: list[tuple[str, Any]] = []  # (col_name, FieldDef)
            for fname, fdef in tdef.fields.items():
                if fname in _SKIP_FIELDS:
                    continue
                if fname in _KEEP_FIELDS:
                    fields.append((fname, fdef))
                else:
                    fields.append((fname, fdef))

            if not fields:
                continue

            col_names = [f[0] for f in fields]
            safe_names = [_safe_ident(n) for n in col_names]
            col_defs = ', '.join(
                f'[{sn}] {_sqlite_type(fdef)}'
                for sn, (_, fdef) in zip(safe_names, fields))

            table_sql = (
                f'CREATE TABLE [{_safe_ident(obj["_full"])}] ({col_defs})')
            con.execute(table_sql)

            # заполнить _columns для этого объекта
            obj_id = con.execute(
                'SELECT id FROM _objects WHERE name = ?',
                (obj['_full'],)).fetchone()[0]
            col_rows: list[tuple[int, str, str, str, int, int]] = []
            for fname, fdef in fields:
                col_rows.append((obj_id, fname, fname,
                                 _model_type_val(fdef),
                                 fdef.length, fdef.precision))
            if col_rows:
                con.executemany(
                    'INSERT INTO _columns (object_id, col_name, field_name, '
                    'type, length, precision) VALUES (?, ?, ?, ?, ?, ?)',
                    col_rows)

            # читаем и вставляем строки
            rows: list[list[Any]] = []
            count = 0
            for row_bytes in db.table_rows(tdef):
                if row_bytes[:1] == b'\x01':
                    continue
                idr = tdef.fields.get('_IDRREF')
                if idr is not None:
                    raw_id = row_bytes[idr.offset:idr.offset + idr.size]
                    if raw_id == b'\x00' * 16:
                        continue  # пустая ссылка — служебная строка

                decoded: list[Any] = []
                for _, fdef in fields:
                    raw = row_bytes[fdef.offset:fdef.offset + fdef.size]
                    try:
                        val = decode_field(fdef, raw)
                    except (ValueError, UnicodeDecodeError):
                        val = None  # битое поле — пропускаем
                    if isinstance(val, bytes):
                        val = None  # BLOB не выгружаем
                    elif isinstance(val, str) and fdef.type in ('RV', 'B') and len(raw) == 16:
                        val = bin_to_guid(raw)  # GUID как текст
                    decoded.append(val)

                rows.append(decoded)
                count += 1
                if limit and count >= limit:
                    break

            if rows:
                placeholders = ', '.join(['?'] * len(safe_names))
                insert_sql = (
                    f'INSERT INTO [{_safe_ident(obj["_full"])}] '
                    f'({", ".join(f"[{sn}]" for sn in safe_names)}) '
                    f'VALUES ({placeholders})')
                con.executemany(insert_sql, rows)

            # обновить row_count
            con.execute(
                'UPDATE _objects SET row_count = ? WHERE name = ?',
                (count, obj['_full']))


def _sqlite_type(fdef: Any) -> str:
    """sqlite-тип по FieldDef."""
    t = fdef.type
    if t in ('NVC', 'NC'):
        return 'TEXT'
    if t == 'N':
        return 'INTEGER' if fdef.precision == 0 else 'REAL'
    if t in ('NT', 'I'):
        return 'INTEGER'
    if t == 'DT':
        return 'TEXT'  # ISO-8601
    if t == 'L':
        return 'INTEGER'  # 0/1
    if t in ('RV', 'B'):
        return 'TEXT'  # GUID-строка
    return 'TEXT'


def _model_type_val(fdef: Any) -> str:
    t = fdef.type
    if t in ('NVC', 'NC'):
        return 'string'
    if t in ('N', 'NT', 'I'):
        return 'number'
    if t == 'DT':
        return 'date'
    if t == 'L':
        return 'bool'
    if t in ('RV', 'B'):
        return 'ref'
    return 'unknown'


def _safe_ident(name: str) -> str:
    """Экранировать имя для использования как идентификатор SQLite."""
    return name.replace('"', '""')
