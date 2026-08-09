"""Типизатор значений xlsx-моста.

Перенос логики .epf «ЗагрузкаДанныхИзТабличногоДокумента_УФ_v2»
(мПривестиКЧислу / мПривестиКДате / ПолучитьВозможныеЗначения):
текст ячейки -> значение Python по описанию типа колонки (C4 макета настроек).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

KIND_NUMBER = 'number'
KIND_STRING = 'string'
KIND_BOOLEAN = 'boolean'
KIND_DATE = 'date'
KIND_REF = 'ref'

TRUE_WORDS = ('да', 'истина', 'включено')
FALSE_WORDS = ('нет', 'ложь', 'выключено')

_DIGITS = re.compile(r'\d+')


@dataclass(frozen=True)
class TypeSpec:
    """Разобранное описание типа колонки (аналог ОписаниеТипов 1С)."""

    kinds: tuple[str, ...]
    ref_type: str = ''          # 'Справочник.X' / 'Документ.X' / 'Перечисление.X'
    str_length: int = 0         # 0 = переменная длина
    str_fixed: bool = False
    num_length: int = 0
    num_precision: int = 0
    num_nonneg: bool = False
    date_parts: str = 'date'    # 'date' | 'time' | 'datetime'


def parse_type_desc(text: str) -> TypeSpec:
    """Разбор строки описания типа (C4 макета): 'число,15,2', 'строка,20,0',
    'булево', 'дата'/'время'/'дата и время', 'Справочник.Контрагенты'."""
    src = text.strip()
    if not src:
        raise ValueError('пустое описание типа')
    if '.' in src:  # ссылка: Справочник.X / Документ.X / Перечисление.X
        return TypeSpec(kinds=(KIND_REF,), ref_type=src)
    parts = [p.strip() for p in src.lower().split(',') if p.strip()]
    kind = parts[0]
    if kind == 'число':
        return TypeSpec(
            kinds=(KIND_NUMBER,),
            num_length=_to_int(parts[1]) if len(parts) > 1 else 0,
            num_precision=_to_int(parts[2]) if len(parts) > 2 else 0,
            num_nonneg=len(parts) > 3,
        )
    if kind == 'строка':
        if len(parts) == 1:
            return TypeSpec(kinds=(KIND_STRING,))
        return TypeSpec(kinds=(KIND_STRING,), str_length=_to_int(parts[1]),
                        str_fixed=len(parts) >= 3)
    if kind == 'булево':
        return TypeSpec(kinds=(KIND_BOOLEAN,))
    if kind == 'дата':
        return TypeSpec(kinds=(KIND_DATE,), date_parts='date')
    if kind == 'время':
        return TypeSpec(kinds=(KIND_DATE,), date_parts='time')
    if kind == 'дата и время':
        return TypeSpec(kinds=(KIND_DATE,), date_parts='datetime')
    raise ValueError(f'неизвестный тип: {kind}')


def type_to_text(spec: TypeSpec) -> str:
    """Обратная сериализация TypeSpec в строку C4 (для записи моста)."""
    kind = spec.kinds[0] if spec.kinds else KIND_STRING
    if kind == KIND_REF:
        return spec.ref_type
    if kind == KIND_NUMBER:
        parts = ['число', str(spec.num_length), str(spec.num_precision)]
        if spec.num_nonneg:
            parts.append('0')
        return ','.join(parts)
    if kind == KIND_STRING:
        if spec.str_length:
            return f'строка,{spec.str_length}' + (',0' if spec.str_fixed else '')
        return 'строка'
    if kind == KIND_BOOLEAN:
        return 'булево'
    if kind == KIND_DATE:
        return {'date': 'дата', 'time': 'время', 'datetime': 'дата и время'}[spec.date_parts]
    return 'строка'


def to_value(spec: TypeSpec, text: str) -> tuple[Any, str]:
    """(значение, примечание) по описанию типа.

    Пустой текст -> (None, '') для примитивов. Примечание непустое — ошибка
    или неоднозначность (аналог «Примечание» в КонтрольЗаполнения .epf).
    """
    text = (text or '').strip()
    if not text:
        return None, ''
    kind = spec.kinds[0] if spec.kinds else KIND_STRING
    if kind == KIND_NUMBER:
        return _to_number(text, spec)
    if kind == KIND_BOOLEAN:
        return _to_boolean(text)
    if kind == KIND_DATE:
        return _to_date(text, spec)
    return text, ''  # строка и ссылка — как есть


def _to_number(text: str, spec: TypeSpec) -> tuple[Any, str]:
    """мПривестиКЧислу: 'да/истина/включено'->1, 'нет/ложь/выключено'->0,
    пробелы убраны, десятичная запятая, проверка по квалификаторам."""
    low = text.lower()
    if low in TRUE_WORDS:
        return 1, ''
    if low in FALSE_WORDS:
        return 0, ''
    cleaned = text.replace(' ', '').replace('\u00a0', '').replace(',', '.')
    try:
        value: Any = float(cleaned) if ('.' in cleaned or 'e' in cleaned.lower()) else int(cleaned)
    except ValueError:
        return 0, 'Неправильный формат числа'
    note = ''
    if spec.num_nonneg and value < 0:
        note = 'Недопустимое числовое значение'
    if spec.num_precision:
        value = round(value, spec.num_precision)
        if isinstance(value, float) and value.is_integer() and spec.num_precision == 0:
            value = int(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return value, note


def _to_boolean(text: str) -> tuple[Any, str]:
    low = text.lower()
    if low in TRUE_WORDS or low == '1':
        return True, ''
    if low in FALSE_WORDS or low == '0':
        return False, ''
    try:
        return float(text.replace(',', '.')) != 0, ''
    except ValueError:
        return False, 'Неправильный формат булева'


def _to_date(text: str, spec: TypeSpec) -> tuple[Any, str]:
    """мПривестиКДате: части даты из строки (любые разделители), год первым
    — перестановка, год < 100 — авто-век (<30 -> 2000+, иначе 1900+)."""
    parts = [int(p) for p in _DIGITS.findall(text)]
    try:
        if spec.date_parts == 'time':
            if len(parts) == 3:
                return time(parts[0], parts[1], parts[2]), ''
            if len(parts) == 6:
                return time(parts[3], parts[4], parts[5]), ''
            raise ValueError
        if len(parts) in (3, 6):
            day, month, year = parts[0], parts[1], parts[2]
            if day >= 1000:  # год указан первым (ГГГГ.ММ.ДД)
                day, year = year, day
            if year < 100:
                year += 2000 if year < 30 else 1900
            if len(parts) == 3:
                return datetime(year, month, day), ''
            return datetime(year, month, day, parts[3], parts[4], parts[5]), ''
        raise ValueError
    except ValueError:
        return None, 'Неправильный формат даты'


def _to_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
