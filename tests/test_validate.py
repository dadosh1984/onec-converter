"""Unit-тесты валидации."""
from onec_converter.intermediate import make_object
from onec_converter.validate import validate_batch, validate_references


def test_counts():
    objs = [make_object('Справочник.A', '1|', ['1'], {}, {}),
            make_object('Справочник.A', '2|', ['2'], {}, {}),
            make_object('Справочник.B', '3|', ['3'], {}, {})]
    r = validate_batch(objs)
    assert r.ok
    assert r.counts['Справочник.A'] == 2


def test_duplicate_key_warns():
    objs = [make_object('Справочник.A', '1|', ['1'], {}, {}),
            make_object('Справочник.A', '2|', ['1'], {}, {})]
    r = validate_batch(objs)
    assert any('дубликат' in w for w in r.warnings)


def test_empty_key_errors():
    r = validate_batch([make_object('Справочник.A', '1|', ['', ''], {}, {})])
    assert not r.ok


def test_broken_ref_detected():
    objs = [make_object('Справочник.A', '1|', ['1'], {}, {'X': 'Справочник.B:9'})]
    r = validate_references(objs)
    assert not r.ok
