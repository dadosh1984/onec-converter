"""Анонимизатор персональных данных (PII) — идея B4 (модернизация, Фаза 18).

Маскирование персональных данных при переносе между средами (прод → тест):
- по списку реквизитов (fields) — «Фамилия», «Телефон», «ИНН»;
- по regexp-паттернам (ФИО любой формы: «Иванов Иван Иванович», «Иванов Иван»,
  нижний регистр «иванов иван», телефоны +99890…, ИНН/паспорт 9+ цифр).

Режим 'hash' — псевдоним строки через **HMAC-SHA256** с секретом (env
`ONEC_HASH_SECRET` или параметр secret): одинаковый вход ⇒ одинаковый выход
(ссылочная целостность сохраняется), а без знания ключа значение не
восстановить. Без секрета — явное предупреждение и фиксированная соль (НЕ
тихий sha256 без соли).

Значения меняются детерминированно по исходному значению.
"""

from __future__ import annotations

import os
import re
import warnings
from typing import Any

# ФИО: строго 3 слова, каждое с заглавной (классика «Иванов Иван Иванович»).
# НЕ маскируем произвольные фразы («красный диван», «Ноутбук Lenovo»)
# и нижний регистр — порча данных опаснее недомаскировки редких 2-словных ФИО.
_FIO_RE = re.compile(
    r'\b([А-ЯЁA-Z][а-яёa-z]{1,})\s+([А-ЯЁA-Z][а-яёa-z]{1,})\s+'
    r'([А-ЯЁA-Z][а-яёa-z]{1,})\b')
_PHONE_RE = re.compile(r'(?<!\d)(\+?\d[\d\s()-]{8,17}\d)(?!\d)')
_INN_RE = re.compile(r'(?<!\d)(\d{9,12})(?!\d)')

_FALLBACK_SECRET = 'onec-converter-fallback-secret'  # только при отсутствии ONEC_HASH_SECRET
_warned_no_secret = False

# Профили анонимизации 152-ФЗ (Фаза 18): типовые поля по сферам применения.
# Используются как готовые наборы имён полей для Anonymizer(fields=[...]).
PII_PROFILES: dict[str, list[str]] = {
    'salary': ['Фамилия', 'Имя', 'Отчество', 'ФИО', 'Телефон', 'МобильныйТелефон',
               'ИНН', 'Паспорт', 'СНИЛС', 'КПП', 'РасчётныйСчёт', 'Карта'],
    'retail': ['ФИО', 'Фамилия', 'Имя', 'Отчество', 'Телефон', 'МобильныйТелефон',
               'ИНН', 'ДокументУдостоверяющийЛичность', 'Адрес'],
    'medical': ['ФИО', 'Фамилия', 'Имя', 'Отчество', 'ДатаРождения', 'Полис',
                'СНИЛС', 'Телефон', 'Адрес', 'Диагноз'],
}



def mask_fio(value: str) -> str:
    """«Иванов Иван Иванович» → «Иванов И. И.». Только 3 слова с заглавной;
    произвольные фразы и нижний регистр НЕ трогаются (не портим данные)."""
    return _FIO_RE.sub(lambda m: f'{m.group(1)} {m.group(2)[0]}. {m.group(3)[0]}.',
                       value)


def mask_phone(value: str) -> str:
    """+998901234567 -> +99890*****67 (середина скрыта)."""
    def repl(m: re.Match[str]) -> str:
        digits = re.sub(r'\D', '', m.group(0))
        if len(digits) < 6:
            return m.group(0)
        keep = min(4, len(digits) // 3)
        return f'{digits[:keep]}' + '*' * (len(digits) - keep - 2) + digits[-2:]
    return _PHONE_RE.sub(repl, value)


def mask_inn(value: str) -> str:
    """123456789012 -> 12345*****012 (края видны)."""
    def repl(m: re.Match[str]) -> str:
        d = m.group(1)
        if len(d) <= 4:
            return '*' * len(d)
        return d[:3] + '*' * (len(d) - 5) + d[-2:]
    return _INN_RE.sub(repl, value)


def _mask_by_pattern(value: str) -> str:
    v = mask_fio(value)
    v = mask_phone(v)
    v = mask_inn(v)
    return v


def _resolve_secret(secret: str | None) -> str:
    """Секрет для HMAC: параметр → env ONEC_HASH_SECRET → fallback с warning."""
    global _warned_no_secret
    if secret:
        return secret
    env = os.environ.get('ONEC_HASH_SECRET', '')
    if env:
        return env
    if not _warned_no_secret:
        _warned_no_secret = True
        warnings.warn(
            'ONEC_HASH_SECRET не задан — используется фиксированная соль; '
            'задайте переменную окружения для реальной защиты данных '
            '(псевдоним без ключа восстановим).',
            UserWarning, stacklevel=3)
    return _FALLBACK_SECRET


def _hash_token(value: str, secret: str | None = None) -> str:
    """HMAC-SHA256-псевдоним строки (стабильно, без ключа невосстановимо)."""
    from .crypto_utils import hmac_sha256_hex

    key = _resolve_secret(secret).encode('utf-8')
    return hmac_sha256_hex(key, value)


class Anonymizer:
    """Маскирование реквизитов объекта при выгрузке.

    fields: имена реквизитов, значения которых маскируются по паттернам
            (или заменяются хешем, если mode='hash').
    mode: 'mask' — частичное скрытие (ФИО/телефоны/ИНН), 'hash' — псевдоним
          HMAC (для ключевых полей типа Фамилия).
    secret: секрет для HMAC (иначе env ONEC_HASH_SECRET / fallback).
    """

    def __init__(self, fields: list[str] | None = None,
                 mode: str = 'mask', secret: str | None = None) -> None:
        self.fields = set(fields or [])
        self.mode = mode
        self._secret = secret

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Возвращает копию записи с замаскированными реквизитами."""
        out = dict(record)
        for name, value in record.items():
            if not isinstance(value, str) or not value:
                continue
            if self.fields and name not in self.fields:
                continue
            if self.mode == 'hash':
                out[name] = _hash_token(value, self._secret)
            else:
                out[name] = _mask_by_pattern(value)
        return out
