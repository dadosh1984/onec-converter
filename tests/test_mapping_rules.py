"""Unit-тесты схемы правил маппинга."""
from onec_converter.mapping import build_prompt, validate_rules


def test_valid_rules():
    rules = {'version': 1,
             'objects': [{'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
                          'key': ['Код'], 'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}],
             'enums': {}}
    assert validate_rules(rules) == []


def test_missing_fields_reported():
    rules = {'version': 1, 'objects': [{'source': 'X', 'target': 'Y'}]}
    errors = validate_rules(rules)
    assert any('attributes' in e for e in errors)


def test_duplicate_pair_reported():
    rules = {'version': 1, 'objects': [
        {'source': 'X', 'target': 'Y', 'attributes': {}},
        {'source': 'X', 'target': 'Y', 'attributes': {}}]}
    assert any('дубликат' in e for e in validate_rules(rules))


def test_build_prompt_mentions_both_sides():
    p = build_prompt({'obj': 1}, {'obj': 2})
    assert 'ИСТОЧНИКА' in p and 'ПРИЁМНИКА' in p
