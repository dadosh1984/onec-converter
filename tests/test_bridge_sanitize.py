"""Безопасные значения для openpyxl:
control-символы, суррогаты и бинарные bytes-поля не ломают запись моста."""
from __future__ import annotations

from pathlib import Path

from onec_converter.bridge_format import _xlsx_clean


def test_control_chars_removed():
    assert _xlsx_clean('a\x00b\x1fc') == 'abc'


def test_surrogates_removed():
    v = 'тест' + '\ud800\udc00' + 'конец'
    out = _xlsx_clean(v)
    assert '\ud800' not in out
    assert 'конец' in out


def test_bytes_become_none():
    assert _xlsx_clean(b'\x00\x01') is None


def test_clean_preserves_normal():
    assert _xlsx_clean('ООО Ромашка & К') == 'ООО Ромашка & К'
    assert _xlsx_clean(123) == 123
    assert _xlsx_clean(None) is None


def test_export_nt_field_does_not_crash(tmp_path, monkeypatch):
    """NT-поле (бинарное) в ТЧ не вызывает IllegalCharacterError при экспорте."""
    from onec_converter.bridge_export import export_bridge
    from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd

    FD = [FixtureField('_IDRREF', 'B', length=16),
          FixtureField('_NUMBER', 'N', length=9)]
    FV = [FixtureField('_DOCUMENT1IDRREF', 'B', length=16),
          FixtureField('_KEYFIELD', 'B', length=16),
          FixtureField('_LINENO2', 'N', length=4),
          FixtureField('_FLD3', 'NVC', length=30),
          FixtureField('_FLD4', 'NT', length=8)]  # бинарное число
    META = {'objects': [
        {'kind': 'Документ', 'name': 'ПриходнаяНакладная', 'table': '_DOCUMENT1',
         'attributes': [
             {'name': 'Номер', 'field': '_NUMBER', 'type': 'number',
              'length': 9, 'precision': 0},
         ]},
    ], 'tables': ['_DOCUMENT1', '_DOCUMENT1_VT2']}
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: dict(META))
    doc_id = bytes.fromhex('02000000110000000000000000000000')
    drow = encode_row(FD, {'_IDRREF': doc_id, '_NUMBER': 1})
    vrow = encode_row(FV, {'_DOCUMENT1IDRREF': doc_id,
                           '_KEYFIELD': b'\x00' * 16,
                           '_LINENO2': 1, '_FLD3': 'Товар А',
                           '_FLD4': b'\x00\x01'})  # bytes
    src = tmp_path / 'src'
    src.mkdir(exist_ok=True)
    (src / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / 'src.1CD',
                       [FixtureTable('_DOCUMENT1', fields=FD, rows=[drow]),
                        FixtureTable('_DOCUMENT1_VT2', fields=FV, rows=[vrow])]))
    bridge = tmp_path / 'vt.xlsx'
    rep = export_bridge(src,
                        'Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2',
                        bridge)
    assert rep['ok'] and rep['rows'] == 1
