"""Сканер персональных данных (ПДн), Фаза 37.

Глубокий поиск ПДн в тексте/значениях: ИНН (12/10), СНИЛС, номера банковских
карт (проверка Луна), телефоны (РФ и Узбекистан +998, ПИНФЛ 14), e-mail.
Профиль UZ добавляет узбекские ИНН/ПИНФЛ. Используется для:
- аудита: не допустить попадания ПДн в журнал (отдельный канал утечки);
- отчётов 152-ФЗ / 152 УЗ: какие поля/значения маскируются.
Код авторский.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ISO-код страны в имени поля → профиль (по умолчанию RU/152-ФЗ).
PII_FIELDS_RU = ('ИНН', 'СНИЛС', 'Паспорт', 'Телефон', 'Сотовый',
                 'Мобильный', 'Email', 'Почта', 'Карта', '№.Карты')
PII_FIELDS_UZ = ('ИНН', 'ПИНФЛ', 'Паспорт', 'Телефон', 'Сотовый',
                 'Мобильный', 'Email', 'Почта', 'Карта')

_INN_RE = re.compile(r'(?<!\d)(\d{12}|\d{10})(?!\d)')
_SNILS_RE = re.compile(r'(?<!\d)(\d{3}[- ]?\d{3}[- ]?\d{3}[- ]?\d{2})(?!\d)')
_PINFL_RE = re.compile(r'(?<!\d)(\d{14})(?!\d)')
_CARD_RE = re.compile(r'(?<!\d)(\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)')
_PHONE_RU_RE = re.compile(r'(?<![\d+])(\+?7[ -(]?\d{3}[ -)]?\d{3}[- ]?\d{2}[- ]?\d{2})'
                          r'|(?<!\d)(\d{3}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2})(?!\d)')
_PHONE_UZ_RE = re.compile(r'(?<![\d+])(\+998)[ -]?\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}')
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')


@dataclass
class PiiMatch:
    kind: str       # 'inn'|'snils'|'card'|'phone'|'email'|'pinfl'
    value: str
    start: int
    end: int


def luhn_valid(number: str) -> bool:
    """Проверка контрольной цифры номера карты по алгоритму Луна."""
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def scan_text(text: str, profile: str = 'RU') -> list[PiiMatch]:
    """Найти фрагменты ПДн в тексте."""
    out: list[PiiMatch] = []
    for m in _INN_RE.finditer(text):
        out.append(PiiMatch('inn', m.group(0), m.start(), m.end()))
    for m in _SNILS_RE.finditer(text):
        out.append(PiiMatch('snils', m.group(0), m.start(), m.end()))
    for m in _CARD_RE.finditer(text):
        raw = re.sub(r'[ -]', '', m.group(0))
        if luhn_valid(raw):  # только реально прошедшие коррекцию Луна
            out.append(PiiMatch('card', m.group(0), m.start(), m.end()))
    for m in _PHONE_RU_RE.finditer(text):
        out.append(PiiMatch('phone', m.group(0), m.start(), m.end()))
    if profile == 'UZ':
        for m in _PHONE_UZ_RE.finditer(text):
            out.append(PiiMatch('phone', m.group(0), m.start(), m.end()))
        for m in _PINFL_RE.finditer(text):
            # 10-ИНН уже отловили; ПИНФЛ — 14 цифр, начинается с 5
            val = m.group(0)
            if val[0] == '5':
                out.append(PiiMatch('pinfl', val, m.start(), m.end()))
    for m in _EMAIL_RE.finditer(text):
        out.append(PiiMatch('email', m.group(0), m.start(), m.end()))
    return out


def scan_value(value: Any, profile: str = 'RU') -> list[PiiMatch]:
    """Сканировать значение (строку/число) на ПДн."""
    if value is None:
        return []
    if isinstance(value, (int, float)):
        value = str(value)
    elif not isinstance(value, str):
        return []
    return scan_text(value, profile=profile)


def field_is_pii(field: str, profile: str = 'RU') -> bool:
    """Является ли имя поля (реквизита) персональным данным."""
    f = (field or '').upper()
    names = PII_FIELDS_UZ if profile == 'UZ' else PII_FIELDS_RU
    return any(k.upper() in f for k in names)


def scan_record(record: dict[str, Any], profile: str = 'RU'
                ) -> list[tuple[str, list[PiiMatch]]]:
    """Сканировать запись {поле: значение}; вернуть ПДн-поля с совпадениями."""
    hits: list[tuple[str, list[PiiMatch]]] = []
    for field, value in record.items():
        if field_is_pii(field, profile):
            matches = scan_value(value, profile)
            if matches:
                hits.append((field, matches))
    return hits
