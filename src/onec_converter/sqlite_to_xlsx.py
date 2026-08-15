"""Конвертация SQLite-таблицы в xlsx-мост для import_bridge.

ponytail: rung 7 — минимальная прослойка между sqlite_automap и epf_load.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .bridge_format import (
    MODE_CATALOG,
    MODE_REGISTER,
    BridgeConfig,
    ColumnSpec,
    write_bridge,
)
from .typify import KIND_STRING, TypeSpec


def sqlite_to_xlsx(
    sqlite_path: str | Path,
    obj_name: str,
    xlsx_out: str | Path,
    mode: int = MODE_CATALOG,
) -> Path:
    """Выгрузить один объект из SQLite в xlsx-мост.

    Args:
        sqlite_path: путь к SQLite (target после apply_mapping)
        obj_name: имя объекта (например, 'Справочник.Номенклатура')
        xlsx_out: путь к создаваемому .xlsx
        mode: MODE_CATALOG для справочников, MODE_REGISTER для регистров

    Returns:
        Path к созданному файлу
    """
    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row

    # Проверяем наличие таблицы
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if obj_name not in tables:
        con.close()
        raise ValueError(f'таблица {obj_name!r} не найдена в SQLite')

    # Читаем данные
    rows_raw = con.execute(f'SELECT * FROM [{obj_name}]').fetchall()
    if not rows_raw:
        con.close()
        out = Path(xlsx_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_bridge(out, BridgeConfig(
            obj_fullname=obj_name, mode=mode, columns=[], first_data_row=2), [])
        return out

    # Колонки из PRAGMA
    cols = con.execute(f'PRAGMA table_info([{obj_name}])').fetchall()
    con.close()

    column_specs: list[ColumnSpec] = []
    for i, col in enumerate(cols):
        col_name = col[1]
        column_specs.append(ColumnSpec(
            flag=True,
            attr=col_name,
            search=(i == 0),  # ponytail: поиск по первой колонке
            type_spec=TypeSpec(kinds=[KIND_STRING]),
            col_num=i + 1,
        ))

    # Строки данных
    data_rows: list[list[Any]] = []
    for row in rows_raw:
        data_rows.append([row[col[1]] for col in cols])

    cfg = BridgeConfig(
        obj_fullname=obj_name,
        mode=mode,
        columns=column_specs,
        first_data_row=2,
    )

    out = Path(xlsx_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_bridge(out, cfg, data_rows)
    return out
