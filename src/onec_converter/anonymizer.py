"""Анонимизатор персональных данных (PII) — идея B4.

Маскирование персональных данных при переносе между средами (прод → тест):
- по списку реквизитов (fields) — «Фамилия», «Телефон», «ИНН»;
- по regexp-паттернам по умолчанию (ФИО вида «Иванов Иван Иванович»,
  телефоны +99890…, ИНН/паспорт 9+ цифр).

Значения меняются необратимо (детерминированно по исходному значению —
одинаковый вход -> одинаковый выход, ссылочная целостность сохраняется).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

_FIO_RE = re.compile(
    r'\b([А-ЯЁA-Z][а-яёa-z]+)\s+([А-ЯЁA-Z][а-яёa-z]+)\s+([А-ЯЁA-Z][а-яёa-z]+)\b')
_PHONE_RE = re.compile(r'(?<!\d)(\+?\d[\d\s()-]{8,17}\d)(?!\d)')
_INN_RE = re.compile(r'(?<!\d)(\d{9,12})(?!\d)')


def mask_fio(value: str) -> str:
    """«Иванов Иван Иванович» -> «Иванов И. И.»."""
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


def _hash_token(value: str) -> str:
    """Детерминированный псевдоним строки (необратимо, но стабильно)."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]


class Anonymizer:
    """Маскирование реквизитов объекта при выгрузке.

    fields: имена реквизитов, значения которых маскируются по паттернам
            (или заменяются хешем, если pattern=False).
    mode: 'mask' — частичное скрытие (ФИО/телефоны/ИНН), 'hash' — полная
          замена хешем (для ключевых полей типа Фамилия).
    """

    def __init__(self, fields: list[str] | None = None,
                 mode: str = 'mask') -> None:
        self.fields = set(fields or [])
        self.mode = mode

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Возвращает копию записи с замаскированными реквизитами."""
        out = dict(record)
        for name, value in record.items():
            if not isinstance(value, str) or not value:
                continue
            if self.fields and name not in self.fields:
                continue
            if self.mode == 'hash':
                out[name] = _hash_token(value)
            else:
                out[name] = _mask_by_pattern(value)
        return out
