"""Единая внутренняя модель данных (версионно-независимая).

Коннекторы всех версий (7.7, 8.x) нормализуют данные в эту модель;
конвейер map/transform/validate/load работает только с ней.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class AttrType:
    """Тип реквизита в нейтральном представлении."""

    kind: Literal['string', 'number', 'date', 'bool', 'ref', 'enum', 'unknown']
    length: int = 0          # для string/number
    precision: int = 0       # для number
    ref_type: str = ''       # для ref: 'Справочник.Банки' и т.п.


@dataclass(frozen=True)
class AttrDef:
    name: str
    type: AttrType


@dataclass
class ObjectType:
    """Тип объекта (справочник/документ/...)."""

    kind: str                # 'Справочник', 'Документ', 'Перечисление', ...
    name: str                # внутреннее имя
    synonym: str = ''
    attributes: list[AttrDef] = field(default_factory=list)
    tabular_sections: dict[str, list[AttrDef]] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f'{self.kind}.{self.name}'


@dataclass
class Record:
    """Одна запись объекта источника (до маппинга)."""

    object_type: ObjectType
    id: str                   # внутренний ID источника ("NNN|" / GUID)
    attributes: dict[str, Any] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)  # имя -> "Тип:ключ|ключ"
    key: tuple[str, ...] = () # естественный ключ (код/наименование)

    def to_intermediate(self) -> dict[str, Any]:
        """Представление для intermediate (XML/JSON)."""
        return {
            'type': self.object_type.full_name,
            'id': self.id,
            'key': list(self.key),
            'attributes': dict(self.attributes),
            'references': dict(self.references),
        }


def build_key(attributes: dict[str, Any], key_attrs: list[str]) -> tuple[str, ...]:
    """Естественный ключ по списку реквизитов (отсутствующие -> '')."""
    return tuple(str(attributes.get(k, '')) for k in key_attrs)
