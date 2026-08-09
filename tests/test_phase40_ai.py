"""Фаза 40: AI-навыки (детерминированные) — auto_map, explain_diff, compress."""
from __future__ import annotations

from pathlib import Path

from onec_converter.ai_skills import auto_map_schemas, compress_metadata, explain_diff

MS = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'synonym': 'Банковские реквизиты',
     'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'type': 'NC'},
                    {'name': 'Наименование', 'type': 'S255'}]},
    {'kind': 'Документ', 'name': 'Продажа', 'synonym': 'Реализация',
     'table': '_DOCUMENT56',
     'attributes': [{'name': 'Номер', 'type': 'NC'},
                    {'name': 'Дата', 'type': 'DT'}]},
]}
MT = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'synonym': '',
     'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'type': 'NC'},
                    {'name': 'Наименование', 'type': 'S255'},
                    {'name': 'БИК', 'type': 'NC'}]},
    {'kind': 'Документ', 'name': 'ПродажаТоваров', 'synonym': 'Реализация',
     'table': '_DOCUMENT99',
     'attributes': [{'name': 'Номер', 'type': 'NC'},
                    {'name': 'Дата', 'type': 'DT'}]},
]}


# ---- auto_map_schemas ----
def test_auto_map_matches_by_name_and_synonym():
    res = auto_map_schemas(MS, MT)
    assert res['ok'] is True
    assert res['matched'] == 2
    rules = {r['source']: r for r in res['rules']}
    # Справочник.Банки — по имени; реквизиты Наименование совпали
    assert 'Справочник.Банки' in rules
    attrs = rules['Справочник.Банки']['attributes']
    assert attrs['Код'] == 'Код'
    # Документ.Продажа сопоставлен по синониму «Реализация»
    assert 'Документ.Продажа' in rules
    assert rules['Документ.Продажа']['target'] == 'Документ.ПродажаТоваров'


def test_auto_map_unmatched():
    only = {'objects': [{'kind': 'Справочник', 'name': 'А', 'synonym': '',
                         'table': 't',
                         'attributes': [{'name': 'X', 'type': 'S'}]}]}
    res = auto_map_schemas(only, MT)
    assert res['matched'] == 0
    assert res['unmatched'] == 1


# ---- explain_diff ----
def test_explain_diff_reasons():
    diff = {'only_source': ['Справочник.Исход', 'Документ.X'],
            'only_target': ['РегистрСведений.New'],
            'type_mismatch': [{'object': 'Справочник.Банки',
                               'attr': 'Код', 'source_type': 'NC',
                               'target_type': 'N'}], 'counts': {}}
    reasons = explain_diff(diff)
    assert any('только в источнике' in r.lower() for r in reasons)
    assert any('только в приёмнике' in r.lower() for r in reasons)
    assert any('изменён тип' in r.lower() for r in reasons)


def test_explain_diff_match():
    assert explain_diff({}) == ['Структуры совпадают.']


# ---- compress_metadata ----
def test_compress_metadata():
    c = compress_metadata(MS, top_tables=5)
    assert c['objects'] == 2
    assert c['kinds']['Справочник'] == 1 and c['kinds']['Документ'] == 1
    assert len(c['top']) == 2
    assert c['total_attrs'] >= 2


def test_compress_top_tables_limit():
    c = compress_metadata({'objects': [MS['objects'][0] for _ in range(30)]},
                          top_tables=3)
    assert len(c['top']) == 3
    assert c['objects'] == 30


# ---- MCP-тулы ----
def test_mcp_has_ai_tools():
    code = Path('src/onec_converter/mcp_server.py').read_text(encoding='utf-8')
    assert "@visible_tool('auto_map_schemas'" in code
    assert "@visible_tool('explain_diff'" in code
