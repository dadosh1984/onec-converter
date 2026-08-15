"""Применение словаря маппинга: перенос данных из источника в приёмник.

Читает _object_mapping + _field_mapping, генерит SQL-запросы
INSERT INTO target ... SELECT ... FROM source с переименованием полей.
Без внешних зависимостей — только stdlib sqlite3.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def apply_mapping(source_path: str | Path,
                  target_path: str | Path) -> dict[str, Any]:
    """Перенести данные из source в target по заполненному словарю маппинга.

    Для каждого объекта из _object_mapping (status='ready'):
    читает _field_mapping, строит INSERT INTO target."target_name"
    SELECT ... FROM source."source_name".

    Returns:
        {'ok': True/False, 'total': N, 'objects': [...], 'rows_copied': N}
    """
    src = Path(source_path)
    tgt = Path(target_path)

    src_con = sqlite3.connect(str(src))
    tgt_con = sqlite3.connect(str(tgt))
    tgt_con.execute('PRAGMA journal_mode=WAL')

    # проверяем что маппинг существует
    has_mapping = src_con.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='_object_mapping'"
    ).fetchone()[0]

    if not has_mapping:
        src_con.close()
        tgt_con.close()
        return {'ok': True, 'total': 0, 'objects': [],
                'message': 'нет _object_mapping — вызовите auto_map_sqlite'}

    # объекты для переноса
    mappings = src_con.execute(
        "SELECT id, source_name, target_name FROM _object_mapping "
        "WHERE status='ready'"
    ).fetchall()

    if not mappings:
        src_con.close()
        tgt_con.close()
        return {'ok': True, 'total': 0, 'objects': [],
                'message': 'нет готовых объектов (status=ready)'}

    report_objects: list[dict[str, Any]] = []
    total_rows = 0

    for om_id, src_name, tgt_name in mappings:
        # колонки для переноса
        fields = src_con.execute(
            "SELECT source_field, target_field, transform "
            "FROM _field_mapping WHERE object_mapping_id=? "
            "AND status='ready' AND transform != 'skip'",
            (om_id,)
        ).fetchall()

        if not fields:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': 'нет полей для переноса',
            })
            continue

        # проверяем что таблицы существуют
        src_tables = _table_names(src_con)
        tgt_tables = _table_names(tgt_con)

        if src_name not in src_tables:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': f'таблица {src_name!r} не найдена в источнике',
            })
            continue

        if tgt_name not in tgt_tables:
            # создаём таблицу в приёмнике по образцу источника
            src_cols_info = src_con.execute(
                f'PRAGMA table_info([{src_name}])'
            ).fetchall()
            if not src_cols_info:
                report_objects.append({
                    'source': src_name, 'target': tgt_name,
                    'rows': 0, 'error': f'нет колонок в таблице источника {src_name!r}',
                })
                continue

            col_defs = ', '.join(
                f'[{c[1]}] {c[2]}' for c in src_cols_info
            )
            tgt_con.execute(
                f'CREATE TABLE IF NOT EXISTS [{tgt_name}] ({col_defs})')
            tgt_con.commit()
            # ponytail: добавили таблицу — теперь INSERT пройдёт

        # строим INSERT INTO ... SELECT
        src_cols: list[str] = []
        tgt_cols: list[str] = []
        for src_field, tgt_field, transform in fields:
            if not tgt_field:
                continue  # ponytail: нет цели — пропускаем
            src_cols.append(f'[{src_field}]')
            tgt_cols.append(f'[{tgt_field}]')

        if not src_cols:
            continue

        sql = (
            f'INSERT OR IGNORE INTO [{tgt_name}] '
            f'({", ".join(tgt_cols)}) '
            f'SELECT {", ".join(src_cols)} '
            f'FROM [{src_name}]'
        )

        try:
            # источник уже ATTACH-нут? Нет — выполняем через src_con
            # ponytail: rung 3 — читаем данные из src, пишем в tgt
            rows = src_con.execute(
                f'SELECT {", ".join(src_cols)} FROM [{src_name}]'
            ).fetchall()

            if rows:
                placeholders = ', '.join(['?'] * len(tgt_cols))
                insert_sql = (
                    f'INSERT OR IGNORE INTO [{tgt_name}] '
                    f'({", ".join(tgt_cols)}) '
                    f'VALUES ({placeholders})')
                tgt_con.executemany(insert_sql, rows)
                tgt_con.commit()

            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': len(rows),
            })
            total_rows += len(rows)

        except sqlite3.Error as e:
            report_objects.append({
                'source': src_name, 'target': tgt_name,
                'rows': 0, 'error': str(e),
            })

    src_con.close()
    tgt_con.close()

    return {
        'ok': True,
        'total': len(report_objects),
        'rows_copied': total_rows,
        'objects': report_objects,
    }


def _table_names(con: sqlite3.Connection) -> set[str]:
    """Имена всех таблиц в базе."""
    return {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
