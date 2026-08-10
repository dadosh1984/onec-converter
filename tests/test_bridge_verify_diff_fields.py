"""diff на уровне полей: для different показывать различающиеся колонки."""
from __future__ import annotations

from types import SimpleNamespace

from onec_converter.bridge_verify import compare_code


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(columns=[
        SimpleNamespace(attr='Код', col_num=1, search=True),
        SimpleNamespace(attr='Наименование', col_num=2, search=False),
        SimpleNamespace(attr='Сумма', col_num=3, search=False),
    ])


def test_diff_has_field_level_details():
    in_rows = [['00001', 'Ромашка', 12.5]]
    out_rows = [['00001', 'Ромашка ИЗМ', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['mismatched'] == 1
    d = cmp['diffs'][0]
    assert d['kind'] == 'different'
    assert d['cols'] == [
        {'col': 'Наименование', 'in': 'Ромашка', 'out': 'Ромашка ИЗМ'},
    ]


def test_diff_multiple_fields():
    in_rows = [['00001', 'Ромашка', 12.5]]
    out_rows = [['00001', 'Поле', 99.0]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    d = cmp['diffs'][0]
    assert len(d['cols']) == 2
    cols = {c['col'] for c in d['cols']}
    assert cols == {'Наименование', 'Сумма'}


def test_diff_no_field_level_for_missing_extra():
    in_rows = [['00001', 'Ромашка', 12.5]]
    out_rows = []
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['diffs'][0]['kind'] == 'missing'
