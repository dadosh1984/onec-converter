"""Селективный перенос по разделам (2).

Фильтр объектов конфигурации для `extract --objects`:
- точный объект: `Справочник.Номенклатура`, `Документ.БанковскиеВыписки`;
- группа: `Справочник.*`, `Документ.*`, `Регистр.*`;
- физическая таблица: `Таблица._REFERENCE3` (для 8.x);
- без фильтра (пустой список) — перенос всех данных (по умолчанию).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectSpec:
    kind: str
    name: str  # '*' — вся группа

    @property
    def is_group(self) -> bool:
        return self.name == '*'

    def __str__(self) -> str:
        return f'{self.kind}.{self.name}'


def parse_objects(specs: list[str]) -> list[ObjectSpec]:
    """Разбор списка спецификаций "Раздел.Имя" или "Раздел.*".

    Поднимает ValueError с понятным сообщением при неверном формате.
    """
    out: list[ObjectSpec] = []
    for raw in specs:
        s = raw.strip()
        if not s:
            continue
        if '.' not in s:
            raise ValueError(
                f'--objects: ожидается "Раздел.Имя" или "Раздел.*", получено: {s!r}')
        kind, name = s.split('.', 1)
        kind = kind.strip()
        name = name.strip()
        if not kind or not name:
            raise ValueError(f'--objects: пустая часть в {s!r}')
        out.append(ObjectSpec(kind, name))
    return out


def selects(specs: list[ObjectSpec], kind: str, name: str,
            table: str = '') -> bool:
    """Совпадает ли объект конфигурации (kind, name; физическая таблица table)
    хотя бы с одной спецификацией фильтра.

    Правила: спецификация `Таблица.X` выбирает физическую таблицу X (по имени);
    спецификация `Раздел.Y` — объект конфигурации (kind==Раздел, name==Y);
    `Раздел.*` — вся группа.
    """
    for spec in specs:
        if spec.kind == 'Таблица':
            if spec.is_group or (table and spec.name == table):
                return True
        elif spec.kind == kind and (spec.is_group or spec.name == name):
            return True
    return False
