"""Unit-тесты резолвера ссылок."""
from onec_converter.intermediate import make_object
from onec_converter.resolver import RefResolver


def test_resolve_by_key():
    objs = [make_object('Справочник.Банки', 'T1', ['0001', 'Банк'], {}, {})]
    r = RefResolver()
    r.build(objs)
    assert r.resolve('Справочник.Банки', ('0001', 'Банк'), 'S1') == 'T1'
    assert r.resolve('Справочник.Банки', ('9999', 'Нет'), 'S2') is None


def test_collision_reported():
    objs = [
        make_object('Справочник.X', 'T1', ['1'], {}, {}),
        make_object('Справочник.X', 'T2', ['1'], {}, {}),
    ]
    r = RefResolver()
    r.build(objs)
    assert any(i.kind == 'collision' for i in r.issues)
