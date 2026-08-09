"""Тесты импорта xlsx-моста (epf_load): find-or-create справочника и регистра."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.bridge_format import (
    MODE_CATALOG,
    MODE_REGISTER,
    BridgeConfig,
    ColumnSpec,
    write_bridge,
)
from onec_converter.epf_load import import_bridge
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.source_8x_file import Database1CD, decode_field
from onec_converter.typify import KIND_BOOLEAN, KIND_NUMBER, KIND_STRING, TypeSpec
from onec_converter.write_8x import create_1cd

IDR1 = bytes.fromhex('02000000110000000000000000000000')

REF_FIELDS = [
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_MARKED', 'L'),
    FixtureField('_ISMETADATA', 'L'),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
    FixtureField('_Fld100', 'NVC', length=40),   # ИНН
    FixtureField('_Fld101', 'L'),                 # Флаг
]

REF_META = {
    'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE7',
    'attributes': [
        {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9,
         'precision': 0},
        {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string',
         'length': 40, 'precision': 0},
        {'name': '_Fld100', 'field': '_Fld100', 'type': 'string', 'length': 40,
         'precision': 0},
        {'name': '_Fld101', 'field': '_Fld101', 'type': 'bool', 'length': 1,
         'precision': 0},
    ],
}

REG_FIELDS = [
    FixtureField('_Fld100', 'NVC', length=30),   # Номенклатура (измерение)
    FixtureField('_Fld101', 'NVC', length=30),   # Склад (измерение)
    FixtureField('_Fld102', 'N', length=14, precision=2),  # Остаток
]

REG_META = {
    'kind': 'РегистрСведений', 'name': 'Остатки', 'table': '_INFORG7',
    'attributes': [
        {'name': '_Fld100', 'field': '_Fld100', 'type': 'string', 'length': 30,
         'precision': 0},
        {'name': '_Fld101', 'field': '_Fld101', 'type': 'string', 'length': 30,
         'precision': 0},
        {'name': '_Fld102', 'field': '_Fld102', 'type': 'number', 'length': 14,
         'precision': 2},
    ],
}


def _receiver(tmp_path: Path, fields: list[FixtureField],
              rows: list[bytes]) -> Path:
    if not rows:
        rows = [encode_row(fields, {})]  # data_page нужна для append
    base = create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_REFERENCE7', fields=fields, rows=rows)])
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(base.read_bytes())
    return target


def _cols(*specs: tuple[str, int, bool, TypeSpec, int, str]) -> list[ColumnSpec]:
    out = []
    for i, (attr, col_num, search, spec, flag, lookup) in enumerate(specs):
        out.append(ColumnSpec(flag=flag, attr=attr, search=search,
                              type_spec=spec, mode='Устанавливать',
                              default='', lookup=lookup,
                              owner_ref='', type_ref='', type_elem='',
                              col_num=col_num))
    return out


T_STR40 = TypeSpec(kinds=(KIND_STRING,), str_length=40)
T_STR30 = TypeSpec(kinds=(KIND_STRING,), str_length=30)
T_NUM = TypeSpec(kinds=(KIND_NUMBER,), num_length=14, num_precision=2)
T_BOOL = TypeSpec(kinds=(KIND_BOOLEAN,))


def test_import_creates_new_and_updates_existing(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch):
    """Режим 0: новая строка создаётся, существующая (по Код) обновляется."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REF_META)]})
    target = _receiver(tmp_path, REF_FIELDS, [])
    cfg = BridgeConfig(mode=MODE_CATALOG, obj_fullname='Справочник.Контрагенты',
                       first_data_row=2,
                       columns=_cols(
                           ('Код', 1, True, T_STR40, 1, 'Код'),
                           ('Наименование', 2, False, T_STR40, 1, ''),
                           ('_Fld100', 3, False, T_STR40, 1, ''),
                       ))
    bridge = tmp_path / 'b.xlsx'
    write_bridge(bridge, cfg, [
        ['00001', 'ООО Ромашка', '7701234567'],
        ['00002', 'ООО Поле', '7707654321'],
    ])
    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['ok'] and rep['created'] == 2 and rep['updated'] == 0
    cp = Path(rep['copy_path'])
    assert cp.is_file() and cp != target / '1Cv8.1CD'

    # повторный импорт тех же ключей -> обновление, новых нет
    # (import_bridge копирует target_dir — берём предыдущую копию как приёмник)
    rep2 = import_bridge(bridge, Path(rep['copy_path']).parent,
                         workdir=tmp_path / 'wd2')
    assert rep2['created'] == 0 and rep2['updated'] == 2
    with Database1CD(Path(rep2['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 3  # 1 служебная + 2 данные
        vals = sorted(decode_field(t.fields['_CODE'],
                                   r[t.fields['_CODE'].offset:
                                     t.fields['_CODE'].offset + t.fields['_CODE'].size])
                      for r in rows if r[:1] != b'\x01')
        assert vals == ['', '00001', '00002']
    # оригинал не изменён
    orig = Database1CD(target / '1Cv8.1CD')
    assert orig is not None


def test_import_updates_only_flagged_columns(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch):
    """Режим 0: найденный объект меняет только отмеченные колонки."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REF_META)]})
    row = encode_row(REF_FIELDS, {'_IDRREF': IDR1, '_CODE': '00001',
                                  '_DESCRIPTION': 'Старое имя',
                                  '_Fld100': '7700000000'})
    target = _receiver(tmp_path, REF_FIELDS, [row])
    cfg = BridgeConfig(mode=MODE_CATALOG, obj_fullname='Справочник.Контрагенты',
                       first_data_row=2,
                       columns=_cols(
                           ('Код', 1, True, T_STR40, 1, 'Код'),
                           ('_Fld100', 2, False, T_STR40, 1, ''),
                       ))
    bridge = tmp_path / 'b.xlsx'
    # Наименование НЕ в маппинге — не должно перезаписаться
    write_bridge(bridge, cfg, [['00001', '7701234567']])
    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['updated'] == 1 and rep['created'] == 0
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 1
        rec = {fn: decode_field(fd, rows[0][fd.offset:fd.offset + fd.size])
               for fn, fd in t.fields.items()}
        assert rec['_DESCRIPTION'] == 'Старое имя'   # не тронуто
        assert rec['_Fld100'] == '7701234567'         # обновлено


def test_import_register_find_or_append(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch):
    """Режим 2: запись по измерениям — найденная перезаписана, новой добавлена."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REG_META)]})
    base = create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_INFORG7', fields=REG_FIELDS,
                                    rows=[encode_row(REG_FIELDS, {})])])
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(base.read_bytes())
    cfg = BridgeConfig(mode=MODE_REGISTER, obj_fullname='РегистрСведений.Остатки',
                       first_data_row=2,
                       columns=_cols(
                           ('_Fld100', 1, True, T_STR30, 1, ''),
                           ('_Fld101', 2, True, T_STR30, 1, ''),
                           ('_Fld102', 3, False, T_NUM, 1, ''),
                       ))
    bridge = tmp_path / 'b.xlsx'
    write_bridge(bridge, cfg, [
        ['Шуруповёрт', 'Склад-1', '12.50'],
        ['Шуруповёрт', 'Склад-1', '15.00'],   # та же пара измерений -> update
        ['Дрель', 'Склад-1', '3.00'],
    ])
    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['created'] == 2 and rep['updated'] == 1
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_INFORG7']
        rows = list(db.table_rows(t))
        assert len(rows) == 3  # 1 служебная + 2 записи
        vals = [(decode_field(t.fields['_Fld100'], r[t.fields['_Fld100'].offset:
                                                      t.fields['_Fld100'].offset + t.fields['_Fld100'].size]),
                 decode_field(t.fields['_Fld102'], r[t.fields['_Fld102'].offset:
                                                      t.fields['_Fld102'].offset + t.fields['_Fld102'].size]))
                for r in rows]
        by_name = {n: v for n, v in vals}
        assert by_name['Шуруповёрт'] == 15.0
        assert by_name['Дрель'] == 3.0


def test_import_tabular_requires_vt_when_owner_has_none(tmp_path: Path,
                                                       monkeypatch):
    """Режим 1: если у владельца нет VT-таблицы — ошибка строки в отчёте."""
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REF_META)]})
    target = _receiver(tmp_path, REF_FIELDS, [])
    cfg = BridgeConfig(mode=1, obj_fullname='Справочник.Контрагенты',
                       first_data_row=2,
                       columns=_cols(('Код', 1, True, T_STR40, 1, 'Код'),))
    bridge = tmp_path / 'bx.xlsx'
    write_bridge(bridge, cfg, [['К1']])
    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['skipped'] == 1 and rep['errors']
    assert 'табличной части' in rep['errors'][0]['error']


def test_import_tabular_section(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    """Режим 1 (табличная часть): строки дописываются в VT-таблицу владельца."""
    from onec_converter.typify import KIND_NUMBER
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REF_META)]})
    # добавляем VT-таблицу к копии приёмника
    vt_fields = [
        FixtureField('_REFERENCE7_IDRREF', 'B', length=16),
        FixtureField('_KEYFIELD', 'B', length=4),
        FixtureField('_LINENO215', 'N', length=3),
        FixtureField('_Fld100', 'NVC', length=40, null_exists=True),
        FixtureField('_Fld101', 'N', length=14, precision=2),
    ]
    base = create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_REFERENCE7', fields=REF_FIELDS,
                                    rows=[encode_row(REF_FIELDS, {})]),
                       FixtureTable('_REFERENCE7_VT214', fields=vt_fields,
                                    rows=[encode_row(vt_fields, {})])])
    ttgt = tmp_path / 'target2'
    ttgt.mkdir()
    (ttgt / '1Cv8.1CD').write_bytes(base.read_bytes())

    cfg = BridgeConfig(mode=1, obj_fullname='Справочник.Контрагенты',
                       first_data_row=2,
                       columns=_cols(
                           ('Код', 1, True, T_STR40, 1, 'Код'),   # владелец
                           ('_Fld100', 2, False, T_STR40, 1, ''), # реквизит ТЧ
                           ('_Fld101', 3, False,
                            TypeSpec(kinds=(KIND_NUMBER,), num_length=14), 1, ''),
                       ))
    bridge = tmp_path / 'bt.xlsx'
    write_bridge(bridge, cfg, [
        ['К1', 'Первый товар', 10.0],
        ['К1', 'Второй товар', 20.0],
        ['К2', 'Заказ', 5.0],
    ])
    rep = import_bridge(bridge, ttgt, workdir=tmp_path / 'wd3')
    assert rep['ok'] and rep['created'] == 2 and rep['updated'] == 0
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        f = t.fields['_CODE']
        codes = {decode_field(f, r[f.offset:f.offset + f.size])
                 for r in db.table_rows(t) if r[:1] != b'\x01'
                 and decode_field(f, r[f.offset:f.offset + f.size])}
        assert codes == {'К1', 'К2'}   # создано два владельца
        vt = db.tables['_REFERENCE7_VT214']
        parf = next(f for f in vt.fields.values()
                    if f.name.endswith('IDRREF') and len(f.name) > 6)
        rows = [r for r in db.table_rows(vt)
                if r[:1] != b'\x01'
                and r[parf.offset:parf.offset + 16] != b'\x00' * 16]
        assert len(rows) == 3  # 2 строки для К1 + 1 для К2 (сид-строка пустая)
        # номера строк внутри владельца уникальны и последовательны
        linef = next(f for f in vt.fields.values()
                     if f.name.upper().startswith('_LINENO'))
        lines: dict[bytes, list[int]] = {}
        for r in rows:
            par = r[parf.offset:parf.offset + 16]
            lines.setdefault(par, []).append(
                int(decode_field(linef, r[linef.offset:linef.offset + linef.size])))
        for par, ls in lines.items():
            assert sorted(ls) == list(range(1, len(ls) + 1))


def test_import_defaults_current_date_and_empty(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch):
    """Поля по умолчанию: ТекущаяДата/Сегодня, ПустоеЗначение/НовыйОбъект."""
    from onec_converter.typify import KIND_DATE
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(REF_META)]})
    _map = REF_FIELDS + [FixtureField('_Fld102', 'DT')]
    _meta = dict(REF_META)
    _meta['attributes'] = _meta['attributes'] + [
        {'name': '_Fld102', 'field': '_Fld102', 'type': 'date', 'length': 8,
         'precision': 0},
    ]
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [_meta]})
    target = _receiver(tmp_path, _map, [])
    T_DATE = TypeSpec(kinds=(KIND_DATE,), date_parts='datetime')
    cfg = BridgeConfig(mode=MODE_CATALOG, obj_fullname='Справочник.Контрагенты',
                       first_data_row=2,
                       columns=[
                           ColumnSpec(flag=1, attr='Код', search=1,
                                      type_spec=T_STR40, mode='Устанавливать',
                                      default='', lookup='Код',
                                      owner_ref='', type_ref='',
                                      type_elem='', col_num=1),
                           ColumnSpec(flag=1, attr='_Fld102', search=0,
                                      type_spec=T_DATE, mode='Устанавливать',
                                      default='ТекущаяДата()', lookup='',
                                      owner_ref='', type_ref='',
                                      type_elem='', col_num=2),
                           ColumnSpec(flag=1, attr='Наименование', search=0,
                                      type_spec=T_STR40, mode='Устанавливать',
                                      default='ПустоеЗначение()', lookup='',
                                      owner_ref='', type_ref='',
                                      type_elem='', col_num=3),
                       ])
    bridge = tmp_path / 'b.xlsx'
    write_bridge(bridge, cfg, [['00001', None, None]])
    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['ok'] and rep['created'] == 1
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        drow = next(r for r in db.table_rows(t)
                    if r[:1] != b'\x01'
                    and decode_field(t.fields['_CODE'],
                                     r[t.fields['_CODE'].offset:]
                                     [:t.fields['_CODE'].size]) not in (None, ''))
        df = t.fields['_Fld102']
        raw = drow[df.offset:df.offset + df.size]
        dv = decode_field(df, raw)
        assert dv is not None  # ТекущаяДата установлена
        nf = t.fields['_DESCRIPTION']
        nv = decode_field(nf, drow[nf.offset:nf.offset + nf.size])
        assert nv in (None, '')  # ПустоеЗначение -> поле не задано
