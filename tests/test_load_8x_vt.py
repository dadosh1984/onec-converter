"""Фаза 15: табличные части (_VT) и реквизиты документа в load_direct."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD, decode_nc, decode_numeric
from onec_converter.write_8x import create_1cd

F_DOC = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_DATE_TIME', 'DT'),
    FixtureField('_NUMBER', 'N', length=8),
    FixtureField('_POSTED', 'L'),
]
F_VT = [
    FixtureField('_DOCUMENT901_IDRREF', 'B', length=16),
    FixtureField('_KEYFIELD', 'B', length=4),
    FixtureField('_LINENO903', 'N', length=5),
    FixtureField('_FLD903', 'NC', length=9),
]

META = {'objects': [
    {'kind': 'Документ', 'name': 'Заказ', 'table': '_DOCUMENT901',
     'attributes': [{'name': 'Номер', 'field': '_NUMBER', 'type': 'N',
                     'length': 8, 'precision': 0},
                    {'name': 'Дата', 'field': '_DATE_TIME', 'type': 'date',
                     'length': 0, 'precision': 0},
                    {'name': 'Проведён', 'field': '_POSTED', 'type': 'bool',
                     'length': 0, 'precision': 0}]},
]}


def _base(tmp_path: Path) -> Path:
    return create_1cd(
        tmp_path / '1Cv8.1CD',
        [
            FixtureTable('_DOCUMENT901', fields=F_DOC,
                         rows=[encode_row(F_DOC, {})]),
            FixtureTable('_DOCUMENT901_VT903', fields=F_VT,
                         rows=[encode_row(F_VT, {})]),
        ])


def test_vt_rows_written_with_parent(tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch):
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    base = _base(tmp_path)
    (tgt / '1Cv8.1CD').write_bytes(base.read_bytes())
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    obj = {
        'type': 'Документ.Заказ', 'key': [77],
        'attributes': {'Номер': 77},
        'references': {},
        'tab_sections': {'Строки': {'rows': [
            {'_FLD903': 'AAA'}, {'_FLD903': 'BBB'},
        ]}},
    }
    rep = load_direct(tgt, [obj], workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    with Database1CD(Path(rep['copy_path'])) as db:
        doc = db.tables['_DOCUMENT901']
        doc_rows = list(db.table_rows(doc))
        fid = doc.fields['_IDRREF']
        base_idref = doc_rows[-1][fid.offset:fid.offset + 16]
        vt = db.tables['_DOCUMENT901_VT903']
        vrows = list(db.table_rows(vt))
        assert len(vrows) == 3  # seed + 2 новых
        p = vt.fields['_DOCUMENT901_IDRREF']
        lf = vt.fields['_LINENO903']
        fld = vt.fields['_FLD903']
        newrows = vrows[-2:]
        for v, lineno, code in zip(newrows, (1, 2), ('AAA', 'BBB')):
            assert v[p.offset:p.offset + 16] == base_idref
            n = decode_numeric(v[lf.offset:lf.offset + lf.size],
                               lf.length, 0)
            assert n == lineno
            assert decode_nc(v[fld.offset:fld.offset + fld.size]) == code


def test_doc_number_date_posted(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    base = _base(tmp_path)
    (tgt / '1Cv8.1CD').write_bytes(base.read_bytes())
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    obj = {
        'type': 'Документ.Заказ', 'key': [123],
        'attributes': {'Номер': 123, 'Дата': '20240101120000',
                       'Проведён': True},
        'references': {},
    }
    rep = load_direct(tgt, [obj], workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    with Database1CD(Path(rep['copy_path'])) as db:
        doc = db.tables['_DOCUMENT901']
        row = list(db.table_rows(doc))[-1]
        nf = doc.fields['_NUMBER']
        n = decode_numeric(row[nf.offset:nf.offset + nf.size], nf.length, 0)
        assert n == 123
        df = doc.fields['_DATE_TIME']
        assert row[df.offset:df.offset + 7] == bytes.fromhex('20240101120000')
        pff = doc.fields['_POSTED']
        assert row[pff.offset] == 1
