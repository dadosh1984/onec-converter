"""--ignore-cols: колонки исключаются из diff (служебные _Version/_Marked)."""
from __future__ import annotations

from types import SimpleNamespace

from onec_converter.bridge_verify import compare_code


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(columns=[
        SimpleNamespace(attr='Код', col_num=1, search=True),
        SimpleNamespace(attr='_VERSION', col_num=2, search=False),
        SimpleNamespace(attr='Сумма', col_num=3, search=False),
    ])


def test_ignore_cols_skips_differences():
    in_rows = [['00001', 'AAAAA', 12.5]]
    out_rows = [['00001', 'BBBBB', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код',
                       ignore_cols=['_VERSION'])
    assert cmp['matched'] == 1 and cmp['mismatched'] == 0


def test_ignore_cols_multiple():
    in_rows = [['00001', 'AAAAA', 1]]
    out_rows = [['00001', 'BBBBB', 2]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код',
                       ignore_cols=['_VERSION', 'Сумма'])
    assert cmp['matched'] == 1 and cmp['ok'] is True


def test_ignore_cols_does_not_hide_real_diff():
    in_rows = [['00001', 'AAAAA', 12.5]]
    out_rows = [['00001', 'BBBBB', 99.0]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код',
                       ignore_cols=['_VERSION'])
    assert cmp['mismatched'] == 1
    d = cmp['diffs'][0]
    assert d['cols'] == [{'col': 'Сумма', 'in': 12.5, 'out': 99.0}]
