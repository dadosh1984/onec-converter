"""Хуки моста: before_write (пропуск/модификация), after_write, «Вычислять»."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.bridge_format import MODE_CATALOG, BridgeConfig, ColumnSpec, write_bridge
from onec_converter.epf_load import import_bridge
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.hooks import before_write, run_hook
from onec_converter.source_8x_file import Database1CD, decode_field
from onec_converter.typify import KIND_STRING, TypeSpec
from onec_converter.write_8x import create_1cd

FIELDS = [
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_MARKED', 'L'),
    FixtureField('_ISMETADATA', 'L'),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]
META = {
    'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
    'attributes': [
        {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9,
         'precision': 0},
        {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string',
         'length': 40, 'precision': 0},
    ],
}
T_STR40 = TypeSpec(kinds=(KIND_STRING,), str_length=40)


def _receiver(tmp_path: Path, rows: list[bytes]) -> Path:
    if not rows:
        rows = [encode_row(FIELDS, {})]
    base = create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_REFERENCE7', fields=FIELDS, rows=rows)])
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(base.read_bytes())
    return target


def _bridge(tmp_path, rows, before='', after='', calc_expr=''):
    mode = 'Вычислять' if calc_expr else 'Устанавливать'
    cfg = BridgeConfig(mode=MODE_CATALOG, obj_fullname='Справочник.Банки',
                       first_data_row=2, before_write=before,
                       after_write=after,
                       columns=[
        ColumnSpec(flag=True, attr='Код', search=True, type_spec=T_STR40,
                   mode='Устанавливать', col_num=1),
        ColumnSpec(flag=True, attr='Наименование', search=False,
                   type_spec=T_STR40, mode=mode, lookup=calc_expr, col_num=2),
    ])
    p = tmp_path / 'b.xlsx'
    write_bridge(p, cfg, rows)
    return p


def _codes(cp: Path) -> list[str]:
    with Database1CD(cp) as db:
        t = db.tables['_REFERENCE7']
        f = t.fields['_CODE']
        return sorted(decode_field(f, r[f.offset:f.offset + f.size])
                      for r in db.table_rows(t)
                      if r[:1] != b'\x01'
                      and decode_field(f, r[f.offset:f.offset + f.size]))


def test_hook_before_skip(tmp_path, monkeypatch):
    """ПередЗаписьюОбъекта: False -> строку пропустить."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    target = _receiver(tmp_path, [])
    b = _bridge(tmp_path, [['001', 'Банк А'], ['002', 'Банк Б']],
                before='values["Код"] != "001"')
    rep = import_bridge(b, target, workdir=tmp_path / 'wd')
    assert rep['created'] == 1 and rep['skipped'] == 1
    assert _codes(Path(rep['copy_path'])) == ['002']


def test_hook_before_modify(tmp_path, monkeypatch):
    """ПередЗаписьюОбъекта: dict -> значения обновлены."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    target = _receiver(tmp_path, [])
    b = _bridge(tmp_path, [['001', 'банк а']],
                before='{"Наименование": values["Наименование"].upper()}')
    rep = import_bridge(b, target, workdir=tmp_path / 'wd')
    assert rep['created'] == 1
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        f = t.fields['_DESCRIPTION']
        names = [decode_field(f, r[f.offset:f.offset + f.size])
                 for r in db.table_rows(t) if r[:1] != b'\x01'
                 and decode_field(f, r[f.offset:f.offset + f.size])]
    assert names == ['БАНК А']


def test_hook_calc_column(tmp_path, monkeypatch):
    """Режим «Вычислять»: значение из выражения, а не из колонки."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(META)]})
    target = _receiver(tmp_path, [])
    b = _bridge(tmp_path, [['001', 'БАНК А']],
                calc_expr='texts["Наименование"].lower()')
    rep = import_bridge(b, target, workdir=tmp_path / 'wd')
    assert rep['created'] == 1
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        f = t.fields['_DESCRIPTION']
        names = [decode_field(f, r[f.offset:f.offset + f.size])
                 for r in db.table_rows(t) if r[:1] != b'\x01'
                 and decode_field(f, r[f.offset:f.offset + f.size])]
    assert names == ['банк а']


def test_run_hook_forms():
    assert run_hook('', {'values': {}}) is None
    assert run_hook('values["a"] + 1', {'values': {'a': 2}}) == 3
    assert run_hook('datetime(2020, 1, 2).year', {}) == 2020
    # sandbox: импорт недоступен
    with pytest.raises((NameError, TypeError, AttributeError)):
        run_hook('__import__("os").getcwd()', {})


def test_before_write_forms():
    ok, vals = before_write('', {'values': {'a': 1}})
    assert ok and vals == {'a': 1}
    ok, vals = before_write('False', {'values': {'a': 1}})
    assert not ok
    ok, vals = before_write('{"a": 5}', {'values': {'a': 1}})
    assert ok and vals == {'a': 5}
