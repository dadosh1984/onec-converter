"""Unit-тесты прямой загрузки в 1CD (Фаза 13): load_8x.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import LoadError, _make_idref, _table_for, load_direct, object_to_row
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import create_1cd

FIELDS = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_MARKED', 'L'),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
    FixtureField('_WEIGHT', 'N', length=12, precision=2),
]

META = {
    'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
    'attributes': [
        {'name': 'Код', 'field': '_CODE', 'type': 'NC', 'length': 9,
         'precision': 0},
        {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'NVC',
         'length': 40, 'precision': 0},
        {'name': 'Вес', 'field': '_WEIGHT', 'type': 'N', 'length': 12,
         'precision': 2},
    ],
}


def _base(tmp_path: Path) -> Path:
    return create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_REFERENCE7', fields=FIELDS,
                                    rows=[encode_row(FIELDS, {})])])


def test_object_to_row_roundtrip(tmp_path: Path):
    """Строка из объекта приёмника читается парсером без потерь."""
    from onec_converter.source_8x_file import decode_field

    base = _base(tmp_path)
    with Database1CD(base) as db:
        table = db.tables['_REFERENCE7']
        obj = {'type': 'Справочник.Банки', 'key': ['00001', 'Банк «А»'],
               'attributes': {'Код': '00001', 'Наименование': 'Банк «А»',
                              'Вес': 12.5}, 'references': {}}
        fm = [type('FM', (), {'name': a['name'], 'field': a['field'],
                              'ftype': a['type'], 'length': a['length'],
                              'precision': a['precision']})
              for a in META['attributes']]
        row = object_to_row(table, fm, obj, b'\x11' * 16)
        rec = {fn: decode_field(fd, row[fd.offset:fd.offset + fd.size])
               for fn, fd in table.fields.items()}
        assert rec['_CODE'] == '00001'
        assert rec['_DESCRIPTION'] == 'Банк «А»'
        assert rec['_WEIGHT'] == 12.5
        assert rec['_MARKED'] == 0


def test_idref_unique():
    a = _make_idref(b'\x11\x22\x33\x44', 0)
    b = _make_idref(b'\x11\x22\x33\x44', 1)
    assert a[:4] == b[:4] == b'\x11\x22\x33\x44'
    assert a != b
    assert len(a) == 16


def test_table_for_missing():
    with pytest.raises(LoadError, match='нет объекта'):
        _table_for('Справочник.Нет', {}, {})


def test_load_direct_synthetic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """load_direct на синтетике (мок метаданных): копия + append + чтение."""
    from onec_converter.source_8x_file import decode_field

    base = _base(tmp_path)
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(base.read_bytes())

    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    objs = [{'type': 'Справочник.Банки', 'key': ['00001', 'Банк А'],
             'attributes': {'Код': '00001', 'Наименование': 'Банк А'},
             'references': {}},
            {'type': 'Справочник.Банки', 'key': ['00002', 'Банк Б'],
             'attributes': {'Код': '00002', 'Наименование': 'Банк Б'},
             'references': {}}]
    rep = load_direct(target, objs, workdir=tmp_path / 'wd')
    assert rep['ok'] is True and rep['total'] == 2
    assert rep['tables'] == {'_REFERENCE7': 3}  # 1 существующая + 2 новые
    cp = Path(rep['copy_path'])
    assert cp.is_file() and cp != target / '1Cv8.1CD'
    with Database1CD(cp) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 3
        last = rows[-1]
        f = t.fields['_CODE']
        assert decode_field(f, last[f.offset:f.offset + f.size]) == '00002'
    # оригинал не изменён
    assert (target / '1Cv8.1CD').read_bytes() == base.read_bytes()


def test_cli_load_direct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    """CLI `load --direct`: батч JSON → копия 1CD приёмника."""
    import json

    from onec_converter.cli import main
    from onec_converter.intermediate import save_json_batch

    base = _base(tmp_path)
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(base.read_bytes())
    batch = tmp_path / 'batch.json'
    save_json_batch([{'type': 'Справочник.Банки', 'key': ['00001', 'Банк А'],
                      'attributes': {'Код': '00001', 'Наименование': 'Банк А'},
                      'references': {}}], batch)

    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    rc = main(['load', '--direct', str(target), '--input', str(batch),
               '--workdir', str(tmp_path / 'wd')])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True and out['total'] == 1
    assert Path(out['copy_path']).is_file()
