"""Строгая валидация данных перед записью в 1CD (, Strict Mode).

Препятствует «тихому» повреждению базы: проверяет длину строк (NVC/NC),
диапазоны дат, границы чисел и корректность GUID-ссылок ДО кодирования.
Дефектное значение → сообщение об ошибке (запись отклоняется или помечается),
а не молчаливая порча.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_GUID_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                      r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


@dataclass
class StrictReport:
    """Результат валидации: список проблем (пусто — запись корректна)."""

    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {'ok': self.ok, 'errors': self.errors[:100]}


def _check_string(ftype: str, length: int, value: str) -> list[str]:
    # NVC: длина в символах не больше length; NC: не больше length.
    if value is None:
        return []
    chars = len(value)
    if chars > length:
        # NVC добавляет 2 байта длины, но символы ограничены length.
        return [f'{ftype}: длина {chars} > {length} (значение {value[:20]!r})']
    return []


def _check_number(length: int, precision: int, value: Any) -> list[str]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return [f'N: не число ({value!r})']
    # N хранит length цифр (BCD); амплитуда ограничена 10^length.
    max_abs = 10 ** length
    if abs(f) > max_abs:
        return [f'N: {value!r} вне диапазона (±10^{length})']
    return []


def _check_date(value: Any) -> list[str]:
    if value is None:
        return []
    s = str(value)
    # 1С даты: YYYYMMDDHHMMSS (14 цифр) и валидная дата.
    if not (re.fullmatch(r'\d{14}', s) or re.fullmatch(r'\d{8}', s)):
        return [f'DT: не дата 1С YYYYMMDD( HHMMSS?) ({s!r})']
    import datetime
    try:
        if len(s) == 14:
            datetime.datetime.strptime(s, '%Y%m%d%H%M%S')
        else:
            datetime.datetime.strptime(s, '%Y%m%d')
    except ValueError as exc:
        return [f'DT: невалидная дата ({s!r}): {exc}']
    return []


def _check_ref(value: Any) -> list[str]:
    if isinstance(value, bytes):
        if len(value) != 16:
            return [f'ref: ссылка должна быть 16 байт, получено {len(value)}']
        return []
    if isinstance(value, str):
        # либо GUID, либо "Тип:ключ1|ключ2" (резолвится позже)
        if ':' in value:
            return []
        if not _GUID_RE.match(value):
            return [f'ref: не GUID ({value!r})']
        return []
    return [f'ref: не строка/байты ({value!r})']


def validate_value(ftype: str, length: int, precision: int, value: Any) -> list[str]:
    """Проблемы значения поля (пусто — корректно). Ну/-выселяются кодировкой."""
    if ftype in ('NVC', 'NC'):
        return _check_string(ftype, length, value)
    if ftype == 'N':
        return _check_number(length, precision, value)
    if ftype == 'DT':
        return _check_date(value)
    if ftype in ('B', 'RV'):
        return _check_ref(value)
    return []


def validate_object(obj: dict[str, Any], fields: list[Any]) -> StrictReport:
    """Валидация объекта по его полям (FieldMap с type/length/precision)."""
    report = StrictReport()
    attrs = obj.get('attributes') or {}
    for fm in fields:
        if fm.name not in attrs:
            continue
        value = attrs[fm.name]
        if value is None:
            continue
        for err in validate_value(fm.ftype, fm.length, fm.precision, value):
            report.errors.append(f'{obj.get("type")}:{fm.name}: {err}')
    return report
