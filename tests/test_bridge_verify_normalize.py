"""Юнит-тесты normalize_value: ложные mismatched при сравнении мостов."""
from __future__ import annotations

from datetime import date, datetime

from onec_converter.bridge_verify import normalize_value


def test_numbers_int_float_equal():
    assert normalize_value(1) == normalize_value(1.0)
    assert normalize_value(12.50) == normalize_value(12.5)


def test_strings_trimmed():
    assert normalize_value(' 1 ') == normalize_value(1)
    assert normalize_value('  Ромашка ') == 'Ромашка'
    assert normalize_value('строка\r\n') == 'строка'


def test_empty_none():
    assert normalize_value('') is None
    assert normalize_value('None') is None
    assert normalize_value('NoneType') is None
    assert normalize_value(None) is None


def test_datetime_iso():
    assert normalize_value(datetime(2026, 1, 2, 3, 4, 5)) == '2026-01-02T03:04:05'
    assert normalize_value(date(2026, 1, 2)) == '2026-01-02'


def test_bool_identity():
    assert normalize_value(True) is True
    assert normalize_value(False) is False
