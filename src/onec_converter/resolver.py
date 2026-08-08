"""Резолвер ссылок по естественным ключам.

В 7.7/8.x ссылки — внутренние ID (числовые "NNN|" / GUID), не совпадающие между базами.
Переносим по естественному ключу (код+наименование). Резолвер строит индекс
"тип объекта -> ключ -> целевой ID приёмника" и разрешает ссылки.
Коллизии (одинаковый ключ у нескольких записей) и отсутствующие ключи — отчёт.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .intermediate import OBJ_ID, OBJ_KEY, OBJ_TYPE


@dataclass
class ResolutionIssue:
    kind: str  # 'collision' | 'missing'
    obj_type: str
    key: tuple[str, ...]
    source_id: str
    detail: str = ''


@dataclass
class RefResolver:
    """Индекс: (тип, кортеж ключа) -> список ID приёмника."""

    _index: dict[tuple[str, tuple[str, ...]], list[str]] = field(default_factory=dict)
    issues: list[ResolutionIssue] = field(default_factory=list)

    def build(self, objects: Iterable[dict[str, Any]]) -> None:
        self._index.clear()
        self.issues.clear()
        by_key: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}
        for obj in objects:
            obj_type = obj[OBJ_TYPE]
            key = tuple(str(p) for p in obj[OBJ_KEY])
            by_key.setdefault((obj_type, key), []).append(obj)
        for (obj_type, key), items in by_key.items():
            ids = [it[OBJ_ID] for it in items]
            self._index[(obj_type, key)] = ids
            if len(items) > 1:
                self.issues.append(ResolutionIssue(
                    'collision', obj_type, key, ids[0],
                    f'ключ не уникален: {len(items)} записей'))

    def resolve(self, obj_type: str, key: tuple[str, ...], source_id: str) -> str | None:
        """Вернуть ID приёмника для ссылки или None при отсутствии."""
        ids = self._index.get((obj_type, key))
        if not ids:
            self.issues.append(ResolutionIssue('missing', obj_type, key, source_id))
            return None
        return ids[0]
