"""Валидация переноса: количество, целостность ссылок, дубликаты, конфликты.

Отчёт содержит ошибки и предупреждения; load не запускается при наличии ошибок.
Финальный verify (сверка источник↔приёмник) строится поверх этого модуля.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .intermediate import OBJ_ATTRS, OBJ_KEY, OBJ_REFS, OBJ_TYPE


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)  # тип -> число объектов

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_batch(objects: Iterable[dict[str, Any]]) -> ValidationResult:
    """Проверка промежуточных объектов перед трансформацией/загрузкой."""
    result = ValidationResult()
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for obj in objects:
        obj_type = obj[OBJ_TYPE]
        result.counts[obj_type] = result.counts.get(obj_type, 0) + 1
        key = tuple(str(p) for p in obj[OBJ_KEY])
        if not key or not any(k for k in key):
            result.add_error(f'пустой ключ у объекта {obj_type}')
        pair = (obj_type, key)
        if pair in seen:
            result.add_warning(f'дубликат ключа {obj_type} {key}')
        seen.add(pair)
        for name, value in (obj[OBJ_ATTRS] or {}).items():
            if isinstance(value, float) and value != value:  # noqa: PLR0124 — проверка NaN
                result.add_error(f'{obj_type} {key}: NaN в реквизите {name}')
    return result


def validate_references(objects: Iterable[dict[str, Any]]) -> ValidationResult:
    """Целостность ссылок: каждая ссылка разрешается в существующий ключ."""
    result = ValidationResult()
    keys = {(obj[OBJ_TYPE], tuple(str(p) for p in obj[OBJ_KEY])) for obj in objects}
    for obj in objects:
        for name, target in (obj[OBJ_REFS] or {}).items():
            if ':' not in target:
                continue
            obj_type, key_part = target.split(':', 1)
            key = tuple(key_part.split('|'))
            if (obj_type, key) not in keys:
                result.add_error(f'{obj[OBJ_TYPE]} {obj[OBJ_KEY]}: битая ссылка {name} -> {target}')
    return result
