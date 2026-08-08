"""Unit-тесты единой модели."""
from onec_converter.model import AttrType, AttrDef, ObjectType, Record, build_key


def test_object_type_full_name():
    t = ObjectType('Справочник', 'Банки')
    assert t.full_name == 'Справочник.Банки'


def test_record_to_intermediate():
    t = ObjectType('Справочник', 'Банки', attributes=[
        AttrDef('Код', AttrType('string', 9)),
        AttrDef('Имя', AttrType('string', 150)),
    ])
    r = Record(t, '193|', {'Код': '00001', 'Имя': 'Банк'}, key=('00001', 'Банк'))
    d = r.to_intermediate()
    assert d['type'] == 'Справочник.Банки'
    assert d['attributes']['Код'] == '00001'


def test_build_key_missing_attr_empty():
    assert build_key({'Код': '1'}, ['Код', 'Имя']) == ('1', '')
