"""Составной ключ: key_col парсится как список колонок через запятую."""
from __future__ import annotations

from types import SimpleNamespace

from onec_converter.bridge_verify import compare_code


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(columns=[
        SimpleNamespace(attr='Код', col_num=1, search=True),
        SimpleNamespace(attr='Наименование', col_num=2, search=False),
        SimpleNamespace(attr='Сумма', col_num=3, search=False),
    ])


def test_composite_key_matches_by_pair():
    in_rows = [['00001', 'Ромашка', 12.5], ['00001', 'Поле', 3.0]]
    out_rows = [['00001', 'Ромашка', 12.5], ['00001', 'Поле', 3.0]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows,
                       key_col='Код,Наименование')
    assert cmp['matched'] == 2 and cmp['mismatched'] == 0


def test_composite_key_distinguishes_same_code():
    # одинаковый Код, разные Наименования — разные ключи, не дубликаты
    in_rows = [['00001', 'Ромашка', 12.5], ['00001', 'Поле', 3.0]]
    out_rows = [['00001', 'Ромашка', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows,
                       key_col='Код,Наименование')
    assert cmp['matched'] == 1 and cmp['missing'] == 1


def test_single_key_compat():
    # по-прежнему работает ключ из одной колонки
    in_rows = [['00001', 'Ромашка', 12.5]]
    out_rows = [['00001', 'Ромашка', 12.5]]
    cmp = compare_code(_cfg(), in_rows, _cfg(), out_rows, key_col='Код')
    assert cmp['matched'] == 1 and cmp['ok'] is True
