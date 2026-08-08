"""Unit-тесты verify."""
from onec_converter.intermediate import make_object
from onec_converter.verify import checksum, verify


def test_full_transfer():
    src = [make_object('Справочник.Банки', '1|', ['0001'], {'Имя': 'Банк'}, {})]
    tgt = [make_object('Справочник.Банки', 'T1', ['0001'], {'Имя': 'Банк'}, {})]
    r = verify(src, tgt)
    assert r.full


def test_missing_detected():
    src = [make_object('Справочник.Банки', '1|', ['0001'], {'Имя': 'Банк'}, {})]
    r = verify(src, [])
    assert not r.full and len(r.missing) == 1


def test_checksum_differs_on_change():
    a = make_object('X', '1|', ['1'], {'A': 'v'}, {})
    b = make_object('X', '1|', ['1'], {'A': 'w'}, {})
    assert checksum(a) != checksum(b)
