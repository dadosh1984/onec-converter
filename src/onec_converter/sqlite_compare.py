"""Сравнение двух SQLite-файлов (источник vs приёмник) через ATTACH + SQL.

Замена compare_user_metadata() из classify.py — теперь сравнение
структуры и состава через SQL, а не Python-циклы.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def compare_sqlite(source_path: str | Path,
                   target_path: str | Path) -> dict[str, Any]:
    """Сравнить пользовательские данные в двух SQLite-файлах.

    ATTACH'ит обе базы к одному соединению и выполняет SQL-запросы
    для поиска расхождений: объекты, колонки, количество строк.

    Returns:
        {'ok': [full_name...],
         'conflict': [{'name', 'kind', 'diff': [...]}],
         'total_source': int,
         'total_target': int}
    """
    src = Path(source_path)
    tgt = Path(target_path)
    if not src.is_file():
        raise FileNotFoundError(f'нет файла: {src}')
    if not tgt.is_file():
        raise FileNotFoundError(f'нет файла: {tgt}')

    con = sqlite3.connect(':memory:')
    con.execute(f"ATTACH DATABASE '{src}' AS src")
    con.execute(f"ATTACH DATABASE '{tgt}' AS tgt")

    total_source = con.execute(
        "SELECT COUNT(*) FROM src._objects WHERE category='user'"
    ).fetchone()[0]
    total_target = con.execute(
        "SELECT COUNT(*) FROM tgt._objects WHERE category='user'"
    ).fetchone()[0]

    ok: list[str] = []
    conflict: list[dict[str, Any]] = []

    # Объекты: есть в источнике, нет в приёмнике
    missing_objects = con.execute('''
        SELECT s.name, s.kind
        FROM src._objects s
        LEFT JOIN tgt._objects t ON s.name = t.name AND s.kind = t.kind
        WHERE s.category = 'user' AND t.id IS NULL
    ''').fetchall()
    for name, kind in missing_objects:
        conflict.append({
            'name': name, 'kind': kind,
            'diff': ['нет объекта в приёмнике'],
        })

    # Колонки: различающиеся типы или отсутствующие
    col_diff = con.execute('''
        SELECT s.name, s.kind, sc.col_name, sc.type AS src_type, tc.type AS tgt_type
        FROM src._objects s
        JOIN src._columns sc ON sc.object_id = s.id
        JOIN tgt._objects t ON t.name = s.name AND t.kind = s.kind
        LEFT JOIN tgt._columns tc ON tc.object_id = t.id AND tc.col_name = sc.col_name
        WHERE s.category = 'user'
          AND (tc.type IS NULL OR sc.type != tc.type)
    ''').fetchall()

    # группируем колоночные расхождения по объектам
    col_by_obj: dict[str, dict[str, Any]] = {}
    for name, kind, col_name, src_type, tgt_type in col_diff:
        if name not in col_by_obj:
            col_by_obj[name] = {'name': name, 'kind': kind, 'diff': []}
        if tgt_type is None:
            col_by_obj[name]['diff'].append(
                f'колонка {col_name!r} отсутствует в приёмнике')
        else:
            col_by_obj[name]['diff'].append(
                f'колонка {col_name!r}: тип {src_type} vs {tgt_type}')

    # Количество строк
    row_counts = con.execute('''
        SELECT s.name, s.kind, s.row_count, t.row_count
        FROM src._objects s
        JOIN tgt._objects t ON s.name = t.name AND s.kind = t.kind
        WHERE s.category = 'user' AND s.row_count != t.row_count
    ''').fetchall()
    for name, kind, src_count, tgt_count in row_counts:
        if name not in col_by_obj:
            col_by_obj[name] = {'name': name, 'kind': kind, 'diff': []}
        col_by_obj[name]['diff'].append(
            f'строк: {src_count} (источник) vs {tgt_count} (приёмник)')

    # Формируем ok: объекты без конфликтов
    conflict_names = set()
    for c in conflict:
        conflict_names.add(c['name'])
    for c in col_by_obj.values():
        conflict_names.add(c['name'])
        conflict.append(c)

    all_source = con.execute(
        "SELECT name FROM src._objects WHERE category='user'"
    ).fetchall()
    for (name,) in all_source:
        if name not in conflict_names:
            ok.append(name)

    ok.sort()
    conflict.sort(key=lambda x: x['name'])

    con.close()
    return {
        'ok': ok,
        'conflict': conflict,
        'total_source': total_source,
        'total_target': total_target,
    }
