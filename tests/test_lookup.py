"""RED-тесты резолвера ссылок по полю поиска (аналог ПолучитьВозможныеЗначения .epf)."""
from __future__ import annotations

from pathlib import Path

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd
from onec_converter.lookup import FieldLookupIndex
from onec_converter.source_8x_file import Database1CD

IDR = bytes.fromhex('02000000110000000000000000000000')
IDR2 = bytes.fromhex('02000000220000000000000000000000')

FIELDS = [
    FixtureField('_IDRREF', 'RV', length=16),
    FixtureField('_VERSION', 'I', length=8),
    FixtureField('_MARKED', 'L', length=1),
    FixtureField('_ISMETADATA', 'L', length=1),
    FixtureField('_CODE', 'NVC', length=9, null_exists=True),
    FixtureField('_DESCRIPTION', 'NVC', length=50, null_exists=True),
]

# физические поля реквизитов (для field_map)
ATTR_FIELDS = [
    FixtureField('_Fld100', 'NVC', length=20, null_exists=True),  # ИНН
    FixtureField('_Fld101', 'NC', length=9),                       # КПП
]


def _base(tmp_path: Path) -> Path:
    all_fields = FIELDS + ATTR_FIELDS
    rows = [
        encode_row(all_fields, {'_IDRREF': IDR, '_CODE': '00001',
                                '_DESCRIPTION': 'ООО Ромашка',
                                '_Fld100': '7701234567'}),
        encode_row(all_fields, {'_IDRREF': IDR2, '_CODE': '00002',
                                '_DESCRIPTION': 'ООО Поле',
                                '_Fld100': '7707654321'}),
    ]
    t = FixtureTable('_Reference77', fields=all_fields, rows=rows)
    path = tmp_path / '1Cv8.1CD'
    write_fake_1cd(path, [t])
    return path


def _field_map() -> dict[str, str]:
    """русское имя реквизита -> физическое поле (как _field_map из load_8x)."""
    return {'ИНН': '_Fld100', 'КПП': '_Fld101'}


def test_build_and_resolve_code(tmp_path: Path):
    path = _base(tmp_path)
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Код')
        assert idx.resolve('Справочник.Контрагенты', 'Код', '00001') == [IDR]
        assert idx.resolve('Справочник.Контрагенты', 'Код', '00002') == [IDR2]
        assert idx.resolve('Справочник.Контрагенты', 'Код', 'нет') == []


def test_resolve_by_name(tmp_path: Path):
    path = _base(tmp_path)
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Наименование')
        assert idx.resolve('Справочник.Контрагенты', 'Наименование', 'ООО Поле') == [IDR2]


def test_resolve_by_attribute(tmp_path: Path):
    path = _base(tmp_path)
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'ИНН')
        assert idx.resolve('Справочник.Контрагенты', 'ИНН', '7701234567') == [IDR]
        assert idx.resolve('Справочник.Контрагенты', 'ИНН', '7707654321') == [IDR2]


def test_resolve_unknown_field_empty(tmp_path: Path):
    path = _base(tmp_path)
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Несуществующее')
        assert idx.resolve('Справочник.Контрагенты', 'Несуществующее', 'x') == []


def test_build_is_idempotent(tmp_path: Path):
    path = _base(tmp_path)
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Код')
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Код')
        assert len(idx.resolve('Справочник.Контрагенты', 'Код', '00001')) == 1


def test_skips_metadata_rows(tmp_path: Path):
    meta_row = encode_row(FIELDS, {'_IDRREF': b'\x03' * 16, '_ISMETADATA': True,
                                   '_CODE': '00003', '_DESCRIPTION': 'Помеченный'})
    t = FixtureTable('_Reference77', fields=FIELDS + ATTR_FIELDS,
                     rows=[meta_row])
    path = tmp_path / '1Cv8.1CD'
    write_fake_1cd(path, [t])
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Контрагенты', '_Reference77',
                        _field_map(), 'Код')
        assert idx.resolve('Справочник.Контрагенты', 'Код', '00003') == []


def test_resolve_by_day_for_dates(tmp_path: Path):
    """«Номер от Дата»: документ находится по дню, без учёта времени."""
    from datetime import datetime
    flds = [
        FixtureField('_IDRREF', 'RV', length=16),
        FixtureField('_VERSION', 'I', length=8),
        FixtureField('_MARKED', 'L', length=1),
        FixtureField('_ISMETADATA', 'L', length=1),
        FixtureField('_NUMBER', 'NVC', length=12, null_exists=True),
        FixtureField('_DATE_TIME', 'DT', ),
    ]
    rows = [
        encode_row(flds, {'_IDRREF': IDR, '_NUMBER': '0001-01',
                          '_DATE_TIME': datetime(2024, 1, 15, 10, 30, 0)}),
        encode_row(flds, {'_IDRREF': IDR2, '_NUMBER': '0001-01',
                          '_DATE_TIME': datetime(2024, 2, 20, 8, 0, 0)}),
    ]
    t = FixtureTable('_Document123', fields=flds, rows=rows)
    path = tmp_path / '1Cv8.1CD'
    write_fake_1cd(path, [t])
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Документ.Счёт', '_Document123', {}, 'Дата')
        # поиск по дню (без времени) находит запись от 15.01.2024
        assert idx.resolve_day('Документ.Счёт', 'Дата',
                               datetime(2024, 1, 15)) == [IDR]
        assert idx.resolve_day('Документ.Счёт', 'Дата',
                               datetime(2024, 1, 15, 23, 59, 59)) == [IDR]
        # точный резолв по полному времени — тоже работает
        assert idx.resolve('Документ.Счёт', 'Дата',
                           datetime(2024, 1, 15, 10, 30, 0)) == [IDR]
        # другой день — пусто
        assert idx.resolve_day('Документ.Счёт', 'Дата',
                               datetime(2024, 3, 1)) == []


def test_resolve_filters_by_owner(tmp_path: Path):
    """Подчинённый справочник: resolve(owner=...) возвращает только записи
    владельца (иерархия в _OWNERIDRREF)."""
    OWN1 = bytes.fromhex('03000000110000000000000000000000')
    IDR3 = bytes.fromhex('03000000330000000000000000000000')
    flds = [
        FixtureField('_IDRREF', 'RV', length=16),
        FixtureField('_VERSION', 'I', length=8),
        FixtureField('_MARKED', 'L', length=1),
        FixtureField('_ISMETADATA', 'L', length=1),
        FixtureField('_OWNERIDRREF', 'B', length=16),  # не-RV: fake_1cd даёт свой offset
        FixtureField('_CODE', 'NVC', length=9, null_exists=True),
    ]
    rows = [
        encode_row(flds, {'_IDRREF': IDR, '_OWNERIDRREF': OWN1, '_CODE': '00001'}),
        encode_row(flds, {'_IDRREF': IDR2, '_OWNERIDRREF': OWN1, '_CODE': '00002'}),
        encode_row(flds, {'_IDRREF': IDR3, '_OWNERIDRREF': b'\x00' * 16,
                          '_CODE': '00003'}),
    ]
    t = FixtureTable('_Reference99', fields=flds, rows=rows)
    path = tmp_path / '1Cv8.1CD'
    write_fake_1cd(path, [t])
    with Database1CD(path) as db:
        idx = FieldLookupIndex()
        idx.build_field(db, 'Справочник.Банк', '_Reference99', {}, 'Код')
        # без фильтра — все 3
        assert len(idx.resolve('Справочник.Банк', 'Код', '00001')) == 1
        # по владельцу OWN1 — только его записи
        assert idx.resolve('Справочник.Банк', 'Код', '00001', owner=OWN1) == [IDR]
        assert idx.resolve('Справочник.Банк', 'Код', '00002', owner=OWN1) == [IDR2]
        # запись без владельца не находится фильтром OWN1
        assert idx.resolve('Справочник.Банк', 'Код', '00003', owner=OWN1) == []
        assert idx.resolve('Справочник.Банк', 'Код', '00003')  # без фильтра есть
