"""Фаза 19: перенос регистров (сведений/накопления) через load_direct."""
from __future__ import annotations

from pathlib import Path

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD, decode_nc, decode_numeric
from onec_converter.write_8x import create_1cd

# Регистр сведений: измерения + ресурс (таблица без _IDRREF у регистра-сведений)
R_FIELDS = [
    FixtureField('_FLD1', 'NC', length=9),      # измерение (код)
    FixtureField('_FLD2', 'N', length=8),       # ресурс (число)
    FixtureField('_SIMPLEKEY', 'B', length=16),
]
META = {'objects': [
    {'kind': 'РегистрСведений', 'name': 'Курсы', 'table': '_INFORG9',
     'attributes': [
         {'name': '_FLD1', 'field': '_FLD1', 'type': 'NC', 'length': 9,
          'precision': 0},
         {'name': '_FLD2', 'field': '_FLD2', 'type': 'N', 'length': 8,
          'precision': 0},
     ]},
]}


def _target(tmp_path: Path) -> Path:
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_INFORG9', fields=R_FIELDS,
                             rows=[encode_row(R_FIELDS, {
                                 '_FLD1': 'seed', '_SIMPLEKEY': b'\x11' * 16})])])
    return tgt


def test_load_register_record(tmp_path, monkeypatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: META)
    objs = [{'type': 'РегистрСведений.Курсы', 'key': ['0001'],
             'attributes': {'_FLD1': '0001', '_FLD2': 42.0}, 'references': {}}]
    rep = load_direct(tgt, objs, workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_INFORG9']
        rows = list(db.table_rows(t))
        assert len(rows) == 2  # seed + новая
        last = rows[-1]
        f1, f2 = t.fields['_FLD1'], t.fields['_FLD2']
        assert decode_nc(last[f1.offset:f1.offset + f1.size]) == '0001'
        assert decode_numeric(last[f2.offset:f2.offset + f2.size],
                              f2.length, 0) == 42.0
