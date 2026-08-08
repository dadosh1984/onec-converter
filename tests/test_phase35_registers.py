"""Фаза 35: регистры (запись строк) и перечисления (auto-маппинг по именам)."""
from __future__ import annotations

from pathlib import Path

from onec_converter.enum_mapper import build_enum_map, map_enum_value, normalize_enum_name
from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row


# ---- enum_mapper ----
def test_normalize_enum_name():
    assert normalize_enum_name('Статус заказа') == 'статус заказа'
    assert normalize_enum_name('  СТАТУС_ЗАКАЗА  ') == 'статус заказа'
    assert normalize_enum_name('Клиент-новый') == 'клиент новый'


def test_build_enum_map_by_name():
    src = ['Активен', 'Закрыт', 'Новый']
    tgt = ['Новый', 'Активен', 'Закрыт']
    m = build_enum_map(src, tgt)
    assert m['активен'] == 'Активен'
    assert m['новый'] == 'Новый'
    # нет совпадения — не попадёт в карту (transform оставит исходное имя)
    m2 = build_enum_map(['Активен', 'X'], ['Закрыт'])
    assert 'активен' not in m2


def test_map_enum_value_str():
    m = {'активен': 'Активен'}
    assert map_enum_value('Активен', m, ['Новый', 'Активен']) == 'Активен'
    assert map_enum_value('Активен', {}, ['Новый', 'Активен']) == 'Активен'  # имя
    assert map_enum_value('Чтото', m, ['А']) == 'Чтото'


def test_map_enum_value_int():
    # индекс -> имя в целевой последовательности
    assert map_enum_value(1, {}, ['Новый', 'Активен']) == 'Активен'
    assert map_enum_value(7, {}, ['А']) == 7  # вне диапазона — без изменений


# ---- регистры: механизм посимвольной записи строк в таблицу _InfoRg ----
def _reg_db(tmp_path: Path) -> tuple[Path, Path]:
    from onec_converter.fake_1cd import encode_row as er
    F = [FixtureField('_VERSION', 'RV', length=2),
         FixtureField('_RECORDER', 'RV', length=16),
         FixtureField('_LINE_NO', 'N', length=6, precision=0),
         FixtureField('_ACTIVE', 'L', length=1),
         FixtureField('_Fld10', 'N', length=10, precision=2)]
    src = tmp_path / 'src'
    src.mkdir()
    cd = src / '1Cv8.1CD'
    anchor = er(F, {'_RECORDER': b'\x00' * 16, '_LINE_NO': 0,
                    '_ACTIVE': True, '_Fld10': 0})
    cd.write_bytes(build_fake_1cd([
        FixtureTable('_InfoRg100', fields=F, rows=[anchor])]))
    return src, F


def test_append_rows_to_register_table(tmp_path: Path):
    """Регистр сведения _InfoRg структурно = таблица; строки пишутся
    append_records (механизм записи остатков)."""
    from onec_converter.write_8x import append_records
    src, F = _reg_db(tmp_path)
    cd = src / '1Cv8.1CD'
    rows = b''.join([
        encode_row(F, {'_RECORDER': b'\x01' * 16,
                       '_LINE_NO': 1, '_ACTIVE': True, '_Fld10': 1250}),
        encode_row(F, {'_RECORDER': b'\x02' * 16,
                       '_LINE_NO': 1, '_ACTIVE': False, '_Fld10': 333}),
    ])
    n = append_records(cd, '_InfoRg100', rows)
    assert n >= 1
    # повторное чтение возвращает все строки (якорь + добавленные)
    from onec_converter.source_8x_file import read_table
    recs = list(read_table(cd, '_InfoRg100'))
    assert len(recs) == 3


# ---- transform: применение enum-маппинга ----
def test_transform_applies_enum_map():
    from onec_converter.resolver import RefResolver
    from onec_converter.transform import transform_object

    obj = {'type': 'РегистрСведений.X',
           'attributes': {'Статус': 'Активен', 'Сумма': 100},
           'references': {}, 'key': ['x']}
    rule = {'source': 'X', 'target': 'Y',
            'attributes': {'Статус': 'СтатусПриёмник', 'Сумма': 'Сумма'}}
    enums = {'Статус': 'Активен'}
    resolver = RefResolver({})

    out = transform_object(obj, rule, resolver, enums=enums)
    attrs = out['attributes']
    assert attrs['СтатусПриёмник'] == 'Активен'
    assert attrs['Сумма'] == 100


def test_transform_enum_dict_mapping():
    from onec_converter.resolver import RefResolver
    from onec_converter.transform import transform_object

    obj = {'type': 'X', 'attributes': {'Пол': 'М'}, 'references': {}, 'key': ['x']}
    rule = {'source': 'A', 'target': 'B', 'attributes': {'Пол': 'ПолПр'}}
    enums = {'Пол': {'М': 'Мужской', 'Ж': 'Женский'}}
    out = transform_object(obj, rule, RefResolver({}), enums=enums)
    assert out['attributes']['ПолПр'] == 'Мужской'
