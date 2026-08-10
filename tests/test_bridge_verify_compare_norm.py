"""compare_code с нормализацией: числовые колонки не дают ложных mismatched."""
from __future__ import annotations

from types import SimpleNamespace

from onec_converter.bridge_verify import compare_code


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(columns=[
        SimpleNamespace(attr='Код', col_num=1, search=True),
        SimpleNamespace(attr='Наименование', col_num=2, search=False),
        SimpleNamespace(attr='Сумма', col_num=3, search=False),
    ])


def test_compare_ignores_float_precision():
    in_rows = [['00001', 'Ромашка', 12.5], ['00002', 'Поле', 3.0]]
    out_rows = [['00001', 'Ромашка', 12.50], ['00002', 'Поле', 3]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['matched'] == 2
    assert cmp['mismatched'] == 0
    assert cmp['missing'] == 0 and cmp['extra'] == 0
    assert cmp['ok'] is True


def test_compare_ignores_string_whitespace():
    in_rows = [['00001', '  Ромашка ', 12.5]]
    out_rows = [['00001', 'Ромашка', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['matched'] == 1 and cmp['mismatched'] == 0


def test_compare_still_detects_real_difference():
    in_rows = [['00001', 'Ромашка', 12.5]]
    out_rows = [['00001', 'Поле', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['mismatched'] == 1
