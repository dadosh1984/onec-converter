"""Человекочитаемый xlsx-отчёт по выгруженным данным (openpyxl).

Один лист на тип объекта; колонки — реквизиты; строки — записи.
Используется для верификации выборки человеком до загрузки в приёмник.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from .intermediate import OBJ_ATTRS, OBJ_KEY, OBJ_TYPE


def build_report(objects: Iterable[dict[str, Any]], out_path: str | Path,
                 max_rows_per_sheet: int = 100_000) -> Path:
    """Сформировать xlsx-отчёт: лист на тип объекта."""
    wb = Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for obj in objects:
        grouped.setdefault(obj[OBJ_TYPE], []).append(obj)

    header_font = Font(bold=True)
    for obj_type, items in grouped.items():
        ws = wb.create_sheet(title=_sheet_title(obj_type))
        attr_names: list[str] = []
        for it in items:
            for name in it[OBJ_ATTRS]:
                if name not in attr_names:
                    attr_names.append(name)
        headers = ['Ключ'] + attr_names
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
        for it in items[:max_rows_per_sheet]:
            row = ['|'.join(str(p) for p in it[OBJ_KEY])]
            for name in attr_names:
                row.append(it[OBJ_ATTRS].get(name))
            ws.append(row)
    out = Path(out_path)
    wb.save(out)
    return out


def _sheet_title(obj_type: str) -> str:
    # имена листов до 31 символа, без запрещённых символов
    title = obj_type.replace('.', '_').replace(':', '_')[:31]
    return title or 'Objects'
