"""Unit-тесты transform."""
import pytest

from onec_converter.intermediate import make_object
from onec_converter.resolver import RefResolver
from onec_converter.transform import TransformError, transform_object


def test_transform_renames_attributes():
    obj = make_object('Справочник.Банки', 'S1', ['0001', 'Банк'],
                      {'Код': '0001', 'Имя': 'Банк'}, {})
    rule = {'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
            'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}
    out = transform_object(obj, rule, RefResolver())
    assert out['attributes'] == {'Код': '0001', 'Наименование': 'Банк'}
    assert out['type'] == 'Справочник.Банки'


def test_transform_resolves_refs():
    targets = [make_object('Справочник.Банки', 'T1', ['0001', 'Банк'], {}, {})]
    resolver = RefResolver()
    resolver.build(targets)
    obj = make_object('Справочник.Организации', 'S2', ['OOO'],
                      {}, {'Банк': 'Справочник.Банки:0001|Банк'})
    rule = {'source': 'x', 'target': 'Справочник.Организации', 'attributes': {}}
    out = transform_object(obj, rule, resolver)
    assert out['references']['Банк'] == 'T1'


def test_transform_missing_attr_raises():
    obj = make_object('X', 'S1', ['1'], {}, {})
    rule = {'source': 'X', 'target': 'Y', 'attributes': {'Нет': 'Да'}}
    with pytest.raises(TransformError):
        transform_object(obj, rule, RefResolver())
