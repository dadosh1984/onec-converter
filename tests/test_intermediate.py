"""Unit-тесты промежуточного формата."""
from onec_converter.intermediate import (
    from_json,
    load_json_batch,
    make_object,
    save_json_batch,
    to_json,
    to_xml,
)


def test_json_roundtrip(tmp_path):
    obj = make_object('Справочник.Банки', '193|', ['00001', 'Банк'],
                      {'Код': '00001', 'Наименование': 'Банк'}, {'Владелец': 'Справочник.Орг:ООО'})
    back = from_json(to_json(obj))
    assert back == obj


def test_xml_contains_fields():
    obj = make_object('Справочник.Банки', '1|', ['0001', 'Банк'], {'Код': '0001'}, {})
    xml = to_xml(obj)
    assert 'Справочник.Банки' in xml
    assert '0001' in xml


def test_batch_roundtrip(tmp_path):
    p = tmp_path / 'data.json'
    objs = [make_object('Справочник.X', '1|', ['1'], {'A': 'v'}, {})]
    save_json_batch(objs, p)
    assert load_json_batch(p) == objs
