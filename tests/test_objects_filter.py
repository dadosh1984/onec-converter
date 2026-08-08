"""Фаза 29.2: селективный перенос — парсер и матчер объектов конфигурации."""

from __future__ import annotations

import pytest

from onec_converter.objects_filter import ObjectSpec, parse_objects, selects


def test_parse_objects_basic():
    specs = parse_objects(['Справочник.Номенклатура',
                           'Документ.БанковскиеВыписки'])
    assert specs == [ObjectSpec('Справочник', 'Номенклатура'),
                     ObjectSpec('Документ', 'БанковскиеВыписки')]


def test_parse_objects_group_and_table():
    specs = parse_objects(['Справочник.*', 'Таблица._REFERENCE3'])
    assert specs[0].is_group
    assert specs[1] == ObjectSpec('Таблица', '_REFERENCE3')


def test_parse_objects_invalid():
    with pytest.raises(ValueError, match='Раздел.Имя'):
        parse_objects(['Номенклатура'])
    with pytest.raises(ValueError, match='пустая часть'):
        parse_objects(['Справочник.'])


def test_selects_exact_and_group():
    specs = parse_objects(['Справочник.Номенклатура', 'Документ.*'])
    assert selects(specs, 'Справочник', 'Номенклатура')
    assert not selects(specs, 'Справочник', 'Контрагенты')
    assert selects(specs, 'Документ', 'БанковскиеВыписки')
    assert selects(specs, 'Документ', 'ЛюбойДокумент')
    assert not selects(specs, 'РегистрСведений', 'Цены')


def test_selects_table_spec():
    specs = parse_objects(['Таблица._REFERENCE3'])
    assert selects(specs, 'Справочник', 'Номенклатура', table='_REFERENCE3')
    assert not selects(specs, 'Справочник', 'Номенклатура', table='_REFERENCE10')
    # группа Таблица.* — любые физические таблицы
    assert selects(parse_objects(['Таблица.*']), 'X', 'Y', table='_REFERENCE3')


def test_selects_empty_filter_all():
    assert not selects([], 'Справочник', 'Номенклатура')
