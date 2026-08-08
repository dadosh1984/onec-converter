"""Тесты генератора фикстур и round-trip с v77_reader."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from onec_converter.v77_reader import V77Reader, parse_dat
from tests.fixtures.gen_dat import make_dat


def test_make_dat_encodes_cp866():
    data = make_dat(unique_ids={1: 2}, references={1: [["11|", "код1", "Имя1"]]})
    text = data.decode('cp866')
    assert '7.70' in text
    assert 'Unique IDs' in text


def test_roundtrip_parser():
    data = make_dat(
        unique_ids={1: 3, 2: 1},
        constants=[(7, ['0|', 20240101, '0|', 0, 0, 0, 100.50])],
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]},
    )
    reader = V77Reader.from_bytes(data)
    assert reader.unique_ids() == {1: 3, 2: 1}
    consts = reader.constants()
    assert consts[0][0] == 7
    refs = reader.references()
    assert refs[1][0] == ['1|', '0001', 'Товар А']


def test_parse_dat_scalars():
    text = '{"7.70","",{"A",{1,"2|",20240101,0.50}}}'
    root = parse_dat(text)
    assert root[0] == '7.70'
    assert root[2][1][2] == 20240101
    assert root[2][1][3] == 0.5
