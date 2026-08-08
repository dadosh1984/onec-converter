"""Unit-тесты парсера 1Cv77.dat."""
from onec_converter.v77_reader import V77Reader, parse_dat, DatSyntaxError
from tests.fixtures.gen_dat import make_dat

import pytest


def test_parse_quoted_escape():
    root = parse_dat('{"a""b"}')
    assert root[0] == 'a"b'


def test_parse_numbers_and_dates():
    root = parse_dat('{1,20241204,0.50,0}')
    assert root == [1, 20241204, 0.5, 0]


def test_parse_syntax_error():
    with pytest.raises(DatSyntaxError):
        parse_dat('{1,2')


def test_reader_sections_from_fixture():
    data = make_dat(unique_ids={1: 2})
    r = V77Reader.from_bytes(data)
    assert 'Unique IDs' in r.sections()
    assert 'References' in r.sections()
    assert r.unique_ids() == {1: 2}


def test_reader_references():
    data = make_dat(references={1: [['1|', '0001', 'Имя']]})
    r = V77Reader.from_bytes(data)
    refs = r.references()
    assert refs[1] == [['1|', '0001', 'Имя']]
    assert r.record_count(1) == 0  # счётчик не задан -> 0
