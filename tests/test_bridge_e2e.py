"""Тесты выгрузки xlsx-моста и сквозной цепочки источник -> мост -> приёмник."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.bridge_export import export_bridge
from onec_converter.bridge_format import read_bridge
from onec_converter.bridge_verify import verify_roundtrip
from onec_converter.epf_load import import_bridge
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd
from onec_converter.source_8x_file import Database1CD, decode_field

FIELDS = [
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_MARKED', 'L'),
    FixtureField('_ISMETADATA', 'L'),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
    FixtureField('_Fld100', 'NVC', length=40),
    FixtureField('_Fld101', 'N', length=14, precision=2),
]

META = {
    'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE7',
    'attributes': [
        {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9,
         'precision': 0},
        {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string',
         'length': 40, 'precision': 0},
        {'name': '_Fld100', 'field': '_Fld100', 'type': 'string', 'length': 40,
         'precision': 0},
        {'name': '_Fld101', 'field': '_Fld101', 'type': 'number', 'length': 14,
         'precision': 2},
    ],
}

IDR1 = bytes.fromhex('02000000110000000000000000000000')
IDR2 = bytes.fromhex('02000000220000000000000000000000')


def _source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    rows = [
        encode_row(FIELDS, {'_IDRREF': IDR1, '_CODE': '00001',
                            '_DESCRIPTION': 'ООО Ромашка',
                            '_Fld100': '7701234567', '_Fld101': 12.5}),
        encode_row(FIELDS, {'_IDRREF': IDR2, '_CODE': '00002',
                            '_DESCRIPTION': 'ООО Поле',
                            '_Fld100': '7707654321', '_Fld101': 3.0}),
    ]
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / 'base.1CD',
                       [FixtureTable('_REFERENCE7', fields=FIELDS, rows=rows)]))
    return src


def test_export_bridge_writes_settings_and_data(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch):
    src = _source(tmp_path, monkeypatch)
    out = tmp_path / 'bridge.xlsx'
    rep = export_bridge(src, 'Справочник.Контрагенты', out)
    assert rep['ok'] and rep['rows'] == 2
    cfg, rows = read_bridge(out)
    assert cfg.obj_fullname == 'Справочник.Контрагенты'
    assert cfg.mode == 0
    assert [c.attr for c in cfg.columns] == ['Код', 'Наименование',
                                             '_Fld100', '_Fld101']
    assert cfg.columns[0].search is True      # Код — поле поиска
    assert cfg.columns[1].search is True      # Наименование — поле поиска
    assert len(rows) == 2
    assert rows[0][0] == '00001'
    assert rows[0][1] == 'ООО Ромашка'


def test_export_skips_predefined_rows(tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    rows = [
        encode_row(FIELDS, {'_IDRREF': IDR1, '_CODE': '00001', '_ISMETADATA': True}),
        encode_row(FIELDS, {'_IDRREF': IDR2, '_CODE': '00002',
                            '_DESCRIPTION': 'Обычная'}),
    ]
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / 'base.1CD',
                       [FixtureTable('_REFERENCE7', fields=FIELDS, rows=rows)]))
    out = tmp_path / 'bridge.xlsx'
    rep = export_bridge(src, 'Справочник.Контрагенты', out)
    assert rep['rows'] == 1
    _, rows = read_bridge(out)
    assert len(rows) == 1 and rows[0][0] == '00002'


def test_e2e_export_then_import(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    """Сквозная цепочка: источник -> xlsx-мост -> копия приёмника -> verify."""
    src = _source(tmp_path, monkeypatch)
    out = tmp_path / 'bridge.xlsx'
    export_bridge(src, 'Справочник.Контрагенты', out)



    # приёмник — пустой справочник той же структуры
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    tgt = tmp_path / 'target'
    tgt.mkdir()
    orig_bytes = write_fake_1cd(
        tmp_path / 'tgt.1CD',
        [FixtureTable('_REFERENCE7', fields=FIELDS,
                      rows=[encode_row(FIELDS, {})])])
    (tgt / '1Cv8.1CD').write_bytes(orig_bytes)

    rep = import_bridge(out, tgt, workdir=tmp_path / 'wd')
    assert rep['ok'] and rep['created'] == 2 and rep['updated'] == 0
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 3  # 1 служебная + 2 перенесённые
        data = [r for r in rows if r[:1] != b'\x01'
                and r[t.fields['_IDRREF'].offset:
                      t.fields['_IDRREF'].offset + 16] != b'\x00' * 16]
        codes = sorted(decode_field(t.fields['_CODE'],
                                    r[t.fields['_CODE'].offset:
                                      t.fields['_CODE'].offset + 18])
                       for r in data)
        assert codes == ['00001', '00002']
        names = {decode_field(t.fields['_CODE'],
                              r[t.fields['_CODE'].offset:
                                t.fields['_CODE'].offset + 18]):
                 decode_field(t.fields['_DESCRIPTION'],
                              r[t.fields['_DESCRIPTION'].offset:
                                t.fields['_DESCRIPTION'].offset
                                + t.fields['_DESCRIPTION'].size])
                 for r in data}
        assert names['00001'] == 'ООО Ромашка'
        assert names['00002'] == 'ООО Поле'
    # оригинал приёмника не изменён
    assert (tgt / '1Cv8.1CD').read_bytes() == orig_bytes


def test_e2e_roundtrip_reverse_verify(tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch):
    """Обратный контроль: после импорта выгружаем из копии приёмника обратно
    в мост и сверяем все колонки с исходным мостом."""
    src = _source(tmp_path, monkeypatch)
    out = tmp_path / 'bridge.xlsx'
    export_bridge(src, 'Справочник.Контрагенты', out)

    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    tgt = tmp_path / 'target'
    tgt.mkdir()
    (tgt / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / 'tgt.1CD',
                       [FixtureTable('_REFERENCE7', fields=FIELDS,
                                     rows=[encode_row(FIELDS, {})])]))
    rep = import_bridge(out, tgt, workdir=tmp_path / 'wd')
    assert rep['created'] == 2

    # обратная выгрузка из копии приёмника + сверка по Код
    vr = verify_roundtrip(Path(rep['copy_path']).parent,
                          Path(rep['copy_path']).parent,
                          'Справочник.Контрагенты', out,
                          workdir=tmp_path / 'vr')
    assert vr['ok'], vr
    assert vr['matched'] == 2 and vr['in_rows'] == 2
    assert vr['mismatched'] == 0 and vr['missing'] == 0 and vr['extra'] == 0
