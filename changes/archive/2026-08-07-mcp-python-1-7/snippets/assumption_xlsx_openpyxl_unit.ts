// GREEN: xlsx-отчёт (openpyxl): выгрузка выборки для верификации человеком
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_xlsx_openpyxl_unit() {
  const files: Record<string, string> = {
    'src/onec_converter/xlsx_report.py': `"""Человекочитаемый xlsx-отчёт по выгруженным данным (openpyxl).

Один лист на тип объекта; колонки — реквизиты; строки — записи.
Используется для верификации выборки человеком до загрузки в приёмник.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import Font

from .intermediate import OBJ_TYPE, OBJ_ATTRS, OBJ_KEY


def build_report(objects: Iterable[dict[str, Any]], out_path: str | Path,
                 max_rows_per_sheet: int = 100_000) -> Path:
    """Сформировать xlsx-отчёт: лист на тип объекта."""
    wb = Workbook()
    wb.remove(wb.active)
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
`,
    'tests/test_xlsx.py': `"""Unit-тесты xlsx-отчёта."""
from openpyxl import load_workbook

from onec_converter.intermediate import make_object
from onec_converter import xlsx_report


def test_report_creates_sheet(tmp_path):
    objs = [
        make_object('Справочник.Банки', '1|', ['0001', 'Банк'], {'Код': '0001', 'Имя': 'Банк'}, {}),
        make_object('Справочник.Банки', '2|', ['0002', 'Филиал'], {'Код': '0002', 'Имя': 'Филиал'}, {}),
    ]
    p = tmp_path / 'report.xlsx'
    xlsx_report.build_report(objs, p)
    wb = load_workbook(p)
    ws = wb.active
    assert ws['A1'].value == 'Ключ'
    assert ws['A2'].value == '0001|Банк'
    assert ws.max_row == 3
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
