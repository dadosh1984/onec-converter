"""Фаза 16: verify после записи (roundtrip без потерь) в load_direct."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import load_direct
from onec_converter.write_8x import create_1cd

F_REFERENCE = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]
META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0},
                    {'name': 'Наименование', 'field': '_DESCRIPTION',
                     'type': 'NVC', 'length': 40, 'precision': 0}]},
]}


def _target(tmp_path: Path) -> Path:
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=F_REFERENCE,
                             rows=[encode_row(F_REFERENCE, {
                                 '_IDRREF': b'\x11' * 16,
                                 '_CODE': '00000', '_DESCRIPTION': 'seed'})])])
    return tgt


def test_verify_after_load_full(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    objs = [
        {'type': 'Справочник.Банки', 'key': ['00001', 'Банк'],
         'attributes': {'Код': '00001', 'Наименование': 'Банк'},
         'references': {}},
        {'type': 'Справочник.Банки', 'key': ['00002', 'Банк 2'],
         'attributes': {'Код': '00002', 'Наименование': 'Банк 2'},
         'references': {}},
    ]
    rep = load_direct(tgt, objs, workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    v = rep.get('verify') or {}
    assert v.get('ok') is True, v
    assert v.get('checked') == 2

