"""Выгрузка данных 1С 7.7 в SQLite через V77Reader.

Один проход 1Cv7.MD + 1Cv7.dat → все справочники/документы/регистры в .sqlite.
Без внешних зависимостей (sqlite3 из stdlib).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .v77_reader import V77Reader


def v77_extract_to_sqlite(
    source_dir: str | Path,
    output_path: str | Path,
    encoding: str = 'cp866',
) -> Path:
    """Выгрузить все объекты 7.7 в SQLite.

    Args:
        source_dir: каталог с 1Cv7.MD и 1Cv7.dat
        output_path: путь к создаваемому .sqlite
        encoding: кодировка .dat (cp866/cp1251)

    Returns:
        Path к созданному файлу
    """
    src = Path(source_dir)
    # Ищем DAT-файл: 1Cv7.dat или 1Cv77.dat
    dat_path = None
    for name in ('1Cv77.dat', '1Cv7.dat'):
        candidate = src / name
        if candidate.is_file():
            dat_path = candidate
            break
    if dat_path is None:
        raise FileNotFoundError(f'нет DAT-файла в: {src}')

    # Метаданные — имена объектов из секций _Names
    reader = V77Reader(dat_path, encoding=encoding)

    # Имена справочников из секций _ReferenceN_Names
    ref_names: dict[int, str] = {}
    for sec_name in reader.sections():
        if sec_name.endswith('_Names') and sec_name.startswith('_Reference'):
            sec = reader._sections.get(sec_name)
            if sec and sec.payload:
                entry = sec.payload[0]
                if isinstance(entry, list) and len(entry) >= 2:
                    ref_names[int(entry[0])] = str(entry[1])

    # Имена документов из секций _DocumentN_Names
    doc_names: dict[int, str] = {}
    for sec_name in reader.sections():
        if sec_name.endswith('_Names') and sec_name.startswith('_Document'):
            sec = reader._sections.get(sec_name)
            if sec and sec.payload:
                entry = sec.payload[0]
                if isinstance(entry, list) and len(entry) >= 2:
                    doc_names[int(entry[0])] = str(entry[1])

    # Fallback: имена из V77Metadata (OLE2), если есть olefile
    try:
        from .v77_metadata import V77Metadata
        v77md = V77Metadata(md_path)
        for obj_def in v77md.object_storages():
            # obj_def.storage: 'Справочник_Number1015' или 'Документ_Number739'
            parts = obj_def.storage.split('_', 1)
            if len(parts) == 2:
                kind, num = parts[0], parts[1]
                if kind == 'Справочник' and int(num) not in ref_names:
                    ref_names[int(num)] = f'{kind}.{num}'
                elif kind == 'Документ' and int(num) not in doc_names:
                    doc_names[int(num)] = f'{kind}.{num}'
        v77md.close()
    except Exception:
        pass  # ponytail: olefile может отсутствовать

    out = Path(output_path)
    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(out))
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')

    _create_meta_tables(con)

    # Собираем объекты
    objects: list[dict[str, Any]] = []

    # Справочники
    refs = reader.references()
    for tid, recs in refs.items():
        name = ref_names.get(tid, f'Справочник.{tid}')
        full = f'Справочник.{name}'
        objects.append({
            'kind': 'Справочник', 'name': full, 'tid': tid, 'records': recs,
            'table_name': f'_Reference{tid}',
        })

    # Документы
    doc_sec = reader._sections.get('Documents')
    if doc_sec:
        for entry in doc_sec.payload:
            if not isinstance(entry, list) or len(entry) < 3:
                continue
            tid = int(entry[0])
            name = doc_names.get(tid, f'Документ.{tid}')
            full = f'Документ.{name}'
            recs = []
            if len(entry) >= 3 and isinstance(entry[2], list):
                recs = entry[2]
            objects.append({
                'kind': 'Документ', 'name': full, 'tid': tid, 'records': recs,
                'table_name': f'_Document{tid}',
            })

    # Регистры накопления
    acc_sec = reader._sections.get('Accumulations')
    if acc_sec:
        for entry in acc_sec.payload:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tid = int(entry[0])
            full = f'РегистрНакопления.{tid}'
            recs = [e for e in entry[1:] if isinstance(e, list)]
            if recs:
                objects.append({
                    'kind': 'РегистрНакопления', 'name': full, 'tid': tid, 'records': recs,
                    'table_name': f'_Accum{tid}',
                })

    # Регистры сведений (если есть)
    reg_sec = reader._sections.get('Registers')
    if reg_sec:
        for entry in reg_sec.payload:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tid = int(entry[0])
            full = f'РегистрСведений.{tid}'
            recs = [e for e in entry[1:] if isinstance(e, list)]
            if recs:
                objects.append({
                    'kind': 'РегистрСведений', 'name': full, 'tid': tid, 'records': recs,
                    'table_name': f'_InfoReg{tid}',
                })
    if acc_sec:
        for entry in acc_sec.payload:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tid = int(entry[0])
            full = f'Регистр.{tid}'
            recs = [e for e in entry[1:] if isinstance(e, list)]
            if recs:
                objects.append({
                    'kind': 'РегистрНакопления', 'name': full, 'tid': tid, 'records': recs,
                    'table_name': f'_Accum{tid}',
                })
    if doc_sec:
        for entry in doc_sec.payload:
            if not isinstance(entry, list) or len(entry) < 3:
                continue
            tid = int(entry[0])
            name = doc_names.get(tid, f'Документ.{tid}')
            full = f'Документ.{name}'
            # entry[2] — массив записей документа
            recs = []
            if len(entry) >= 3 and isinstance(entry[2], list):
                # entry[2] может быть [запись1, запись2, ...] или [[тч1], [тч2], ...]
                recs = entry[2]
            objects.append({
                'kind': 'Документ', 'name': full, 'tid': tid, 'records': recs,
                'table_name': f'_Document{tid}',
            })

    # INSERT _objects + CREATE TABLE + данные
    for i, obj in enumerate(objects):
        con.execute(
            'INSERT INTO _objects (kind, name, table_name, category) VALUES (?, ?, ?, ?)',
            (obj['kind'], obj['name'], obj['table_name'], 'user'))

        if not obj['records']:
            continue

        # Определяем колонки по первой записи
        first = obj['records'][0]
        if not first:
            continue
        n_cols = len(first)
        col_defs = ', '.join(f'c{i} TEXT' for i in range(n_cols))
        safe_name = obj['name'].replace('"', '""')
        con.execute(f'CREATE TABLE [{safe_name}] ({col_defs})')

        # INSERT строк (вложенные списки → repr)
        placeholders = ', '.join(['?'] * n_cols)
        # Преобразуем вложенные списки/кортежи в repr чтобы SQLite их принял
        rows: list[tuple] = []
        for r in obj['records']:
            if len(r) != n_cols:
                continue
            flat = tuple(
                repr(v) if isinstance(v, (list, tuple, dict)) else v
                for v in r
            )
            rows.append(flat)
        if rows:
            cols = ', '.join(f'c{i}' for i in range(n_cols))
            con.executemany(
                f'INSERT INTO [{safe_name}] ({cols}) VALUES ({placeholders})', rows)

        # row_count
        con.execute('UPDATE _objects SET row_count = ? WHERE name = ?',
                    (len(rows), obj['name']))

    con.commit()
    con.close()
    return out


def _create_meta_tables(con: sqlite3.Connection) -> None:
    con.execute('''CREATE TABLE _objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
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
