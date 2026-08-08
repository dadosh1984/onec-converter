// GREEN: model.py — единая внутренняя модель (объекты, реквизиты, ссылки, типы)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function fact_model_py_unit() {
  const files: Record<string, string> = {
    'src/onec_converter/model.py': `"""Единая внутренняя модель данных (версионно-независимая).

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
`,
    'tests/test_model.py': `"""Unit-тесты единой модели."""
from onec_converter.model import AttrType, AttrDef, ObjectType, Record, build_key


def test_object_type_full_name():
    t = ObjectType('Справочник', 'Банки')
    assert t.full_name == 'Справочник.Банки'


def test_record_to_intermediate():
    t = ObjectType('Справочник', 'Банки', attributes=[
        AttrDef('Код', AttrType('string', 9)),
        AttrDef('Имя', AttrType('string', 150)),
    ])
    r = Record(t, '193|', {'Код': '00001', 'Имя': 'Банк'}, key=('00001', 'Банк'))
    d = r.to_intermediate()
    assert d['type'] == 'Справочник.Банки'
    assert d['attributes']['Код'] == '00001'


def test_build_key_missing_attr_empty():
    assert build_key({'Код': '1'}, ['Код', 'Имя']) == ('1', '')
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
