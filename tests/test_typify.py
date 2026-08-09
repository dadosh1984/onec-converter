"""RED-тесты типизатора значений xlsx-моста (аналог мПривестиКЧислу/мПривестиКДате .epf)."""
from __future__ import annotations

from datetime import datetime, time

import pytest

from onec_converter.typify import (
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_NUMBER,
    KIND_REF,
    KIND_STRING,
    TypeSpec,
    parse_type_desc,
    to_value,
)

# --- parse_type_desc ---------------------------------------------------------

def test_parse_number():
    s = parse_type_desc('число,15,2')
    assert s.kinds == (KIND_NUMBER,)
    assert s.num_length == 15
    assert s.num_precision == 2
    assert not s.num_nonneg


def test_parse_number_nonneg():
    s = parse_type_desc('число,10,0,0')
    assert s.num_nonneg


def test_parse_number_upper():
    s = parse_type_desc('ЧИСЛО,10,0')
    assert s.kinds == (KIND_NUMBER,)


def test_parse_string_variable():
    s = parse_type_desc('строка,20')
    assert s.kinds == (KIND_STRING,)
    assert s.str_length == 20
    assert not s.str_fixed


def test_parse_string_fixed():
    s = parse_type_desc('строка,20,0')
    assert s.str_fixed


def test_parse_string_plain():
    s = parse_type_desc('строка')
    assert s.str_length == 0


def test_parse_boolean():
    assert parse_type_desc('булево').kinds == (KIND_BOOLEAN,)


def test_parse_date_variants():
    assert parse_type_desc('дата').date_parts == 'date'
    assert parse_type_desc('время').date_parts == 'time'
    assert parse_type_desc('дата и время').date_parts == 'datetime'


def test_parse_ref():
    s = parse_type_desc('Справочник.Контрагенты')
    assert s.kinds == (KIND_REF,)
    assert s.ref_type == 'Справочник.Контрагенты'


def test_parse_ref_document():
    assert parse_type_desc('Документ.ЗаказКлиента').ref_type == 'Документ.ЗаказКлиента'


def test_parse_ref_enum():
    assert parse_type_desc('Перечисление.ВидыНоменклатуры').ref_type == 'Перечисление.ВидыНоменклатуры'


def test_parse_unknown_kind_raises():
    with pytest.raises(ValueError):
        parse_type_desc('неизвестныйтип')


# --- to_value: числа ---------------------------------------------------------

def test_number_plain():
    v, note = to_value(TypeSpec(kinds=(KIND_NUMBER,), num_precision=2), '123')
    assert v == 123 and note == ''


def test_number_decimal_comma():
    v, _ = to_value(TypeSpec(kinds=(KIND_NUMBER,), num_precision=2), '12,5')
    assert v == 12.5


def test_number_strips_spaces():
    v, _ = to_value(TypeSpec(kinds=(KIND_NUMBER,)), '1 000')
    assert v == 1000


def test_number_words_true():
    for word in ('да', 'истина', 'включено', 'ДА', 'Истина'):
        v, _ = to_value(TypeSpec(kinds=(KIND_NUMBER,)), word)
        assert v == 1, word


def test_number_words_false():
    for word in ('нет', 'ложь', 'выключено'):
        v, _ = to_value(TypeSpec(kinds=(KIND_NUMBER,)), word)
        assert v == 0, word


def test_number_bad_format_note():
    v, note = to_value(TypeSpec(kinds=(KIND_NUMBER,)), 'abc')
    assert v == 0
    assert note != ''


def test_number_negative():
    v, _ = to_value(TypeSpec(kinds=(KIND_NUMBER,)), '-5')
    assert v == -5


def test_number_nonneg_rejects():
    v, note = to_value(TypeSpec(kinds=(KIND_NUMBER,), num_nonneg=True), '-5')
    assert v == -5 and note != ''


# --- to_value: булево --------------------------------------------------------

def test_boolean_true_false():
    assert to_value(TypeSpec(kinds=(KIND_BOOLEAN,)), 'да')[0] is True
    assert to_value(TypeSpec(kinds=(KIND_BOOLEAN,)), 'нет')[0] is False
    assert to_value(TypeSpec(kinds=(KIND_BOOLEAN,)), '1')[0] is True
    assert to_value(TypeSpec(kinds=(KIND_BOOLEAN,)), '0')[0] is False


# --- to_value: строка --------------------------------------------------------

def test_string_trimmed():
    v, _ = to_value(TypeSpec(kinds=(KIND_STRING,)), '  Привет  ')
    assert v == 'Привет'


def test_string_empty_is_none():
    v, _ = to_value(TypeSpec(kinds=(KIND_STRING,)), '')
    assert v is None


# --- to_value: даты ----------------------------------------------------------

def test_date_dd_mm_yyyy():
    v, _ = to_value(TypeSpec(kinds=(KIND_DATE,)), '01.02.2020')
    assert v == datetime(2020, 2, 1)


def test_date_year_first_swapped():
    v, _ = to_value(TypeSpec(kinds=(KIND_DATE,)), '2020.02.01')
    assert v == datetime(2020, 2, 1)


def test_date_century_auto():
    assert to_value(TypeSpec(kinds=(KIND_DATE,)), '01.02.20')[0] == datetime(2020, 2, 1)
    assert to_value(TypeSpec(kinds=(KIND_DATE,)), '01.02.95')[0] == datetime(1995, 2, 1)


def test_date_with_time():
    v, _ = to_value(TypeSpec(kinds=(KIND_DATE,)), '01.02.2020 12:30:45')
    assert v == datetime(2020, 2, 1, 12, 30, 45)


def test_time_only():
    v, _ = to_value(TypeSpec(kinds=(KIND_DATE,), date_parts='time'), '12:30:45')
    assert v == time(12, 30, 45)


def test_date_bad_format_note():
    v, note = to_value(TypeSpec(kinds=(KIND_DATE,)), 'не дата')
    assert v is None and note != ''


def test_datetime_parts_enum():
    v, _ = to_value(TypeSpec(kinds=(KIND_DATE,), date_parts='datetime'), '01.02.2020 12:30:45')
    assert isinstance(v, datetime)


# --- to_value: ссылки --------------------------------------------------------

def test_ref_returns_text():
    s = TypeSpec(kinds=(KIND_REF,), ref_type='Справочник.Контрагенты')
    v, note = to_value(s, 'ООО Ромашка')
    assert v == 'ООО Ромашка'
    assert note == ''
