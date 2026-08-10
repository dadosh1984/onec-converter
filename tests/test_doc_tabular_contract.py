"""Контракт документов и ТЧ в xlsx-мосте (bridge-migrate)."""
from __future__ import annotations

from onec_converter.bridge_export import _split_fullname
from onec_converter.epf_load import _split_owner
from onec_converter.classify import build_plan

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты'},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная', 'table': '_DOCUMENT1'},
    {'kind': 'Документ', 'name': 'Счет', 'table': '_DOCUMENT2'},
    {'kind': 'Отчет', 'name': 'ОСВ'},
], 'tables': ['_DOCUMENT1', '_DOCUMENT1_VT2', '_DOCUMENT2', '_DOCUMENT2_VT3',
             '_DOCUMENT2_VT4']}


def test_split_fullname_catalog():
    assert _split_fullname('Справочник.Контрагенты') == ('Справочник', 'Контрагенты', '')


def test_split_fullname_tabular():
    assert _split_fullname('Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2') == \
        ('Документ', 'ПриходнаяНакладная', '_DOCUMENT1_VT2')


def test_split_owner_table():
    assert _split_owner('Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2') == \
        ('Документ.ПриходнаяНакладная', '_DOCUMENT1_VT2')


def test_plan_includes_document_and_each_tabular():
    names = [p['name'] for p in build_plan(META)]
    assert 'Документ.ПриходнаяНакладная' in names
    assert 'Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2' in names
    # документ с двумя ТЧ — два отдельных раздела
    assert 'Документ.Счет.ТЧ._DOCUMENT2_VT3' in names
    assert 'Документ.Счет.ТЧ._DOCUMENT2_VT4' in names
    assert 'Отчет.ОСВ' not in names
