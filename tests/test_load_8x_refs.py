"""Фаза 15: REF-запись в load_direct — резолв в _IDRREF приёмника по ключу."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import create_1cd

F_REFERENCE = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]
F_DOC = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_NUMBER', 'N', length=8),
    FixtureField('_FLD901RREF', 'B', length=16),
]

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0}]},
    {'kind': 'Документ', 'name': 'Заказ', 'table': '_DOCUMENT901',
     'attributes': [{'name': 'Номер', 'field': '_NUMBER', 'type': 'N',
                     'length': 8, 'precision': 0},
                    {'name': '_FLD901RREF', 'field': '_FLD901RREF',
                     'type': 'ref', 'length': 16, 'precision': 0}]},
]}


def _base(tmp_path: Path) -> Path:
    return create_1cd(
        tmp_path / '1Cv8.1CD',
        [
            FixtureTable('_REFERENCE7', fields=F_REFERENCE,
                         rows=[encode_row(F_REFERENCE,
                                          {'_IDRREF': b'\x11' * 16,
                                           '_CODE': '00001',
                                           '_DESCRIPTION': 'Банк'})]),
            FixtureTable('_DOCUMENT901', fields=F_DOC,
                         rows=[encode_row(F_DOC, {})]),
        ])


def _target(tmp_path: Path) -> Path:
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    base = _base(tmp_path)
    (tgt / '1Cv8.1CD').write_bytes(base.read_bytes())
    return tgt


def _ref_idref(db: Database1CD, table: str) -> bytes:
    t = db.tables[table]
    row = next(iter(db.table_rows(t)))
    f = t.fields['_IDRREF']
    return row[f.offset:f.offset + 16]


def test_ref_field_written_from_target_index(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    obj = {
        'type': 'Документ.Заказ', 'key': [99],
        'attributes': {'Номер': 99},
        'references': {'_FLD901RREF': 'Справочник.Банки:00001|Банк'},
    }
    rep = load_direct(tgt, [obj], workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    with Database1CD(Path(rep['copy_path'])) as db:
        ref_idref = _ref_idref(db, '_REFERENCE7')
        doc = db.tables['_DOCUMENT901']
        rows = list(db.table_rows(doc))
        assert len(rows) == 2  # seed + записанный
        f = doc.fields['_FLD901RREF']
        written = rows[-1][f.offset:f.offset + 16]
        assert written == ref_idref, (written.hex(), ref_idref.hex())
        assert rep.get('ref_warnings') == []


def test_missing_ref_zeros_and_reported(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    obj = {
        'type': 'Документ.Заказ', 'key': [1],
        'attributes': {'Номер': 1},
        'references': {'_FLD901RREF': 'Справочник.Банки:99999|НЕСУЩЕСТВ'},
    }
    rep = load_direct(tgt, [obj], workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    with Database1CD(Path(rep['copy_path'])) as db:
        doc = db.tables['_DOCUMENT901']
        rows = list(db.table_rows(doc))
        f = doc.fields['_FLD901RREF']
        assert rows[-1][f.offset:f.offset + 16] == b'\x00' * 16
    assert any('99999' in w for w in rep.get('ref_warnings', []))
