"""Структура приёмника 8.3 и привязка пары источник→приёмник (правило 1→1).

Два источника метаданных приёмника:
1. Прямое чтение 1Cv8.1CD приёмника собственным парсером (source_8x_file);
2. /metadata HTTP-сервиса расширения (когда сервис запущен).

Правило «1→1»: проект переноса хранит привязку (source_ib_id -> target_ib_id)
в файле проекта; загрузка разрешена только при совпадении пары.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProjectError(Exception):
    """Ошибка привязки проекта/правила 1→1."""


@dataclass
class ProjectBinding:
    """Привязка пары ИБ (одна передающая = одна принимающая)."""

    project_dir: Path
    source_ib_id: str
    target_ib_id: str

    _FILE = 'project.json'

    @classmethod
    def create(cls, project_dir: str | Path, source_ib_id: str, target_ib_id: str) -> ProjectBinding:
        p = Path(project_dir)
        p.mkdir(parents=True, exist_ok=True)
        data = {'source_ib_id': source_ib_id, 'target_ib_id': target_ib_id}
        (p / cls._FILE).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
        return cls(p, source_ib_id, target_ib_id)

    @classmethod
    def load(cls, project_dir: str | Path) -> ProjectBinding:
        p = Path(project_dir)
        f = p / cls._FILE
        if not f.is_file():
            raise ProjectError(f'нет проекта переноса: {f}')
        data = json.loads(f.read_text(encoding='utf-8'))
        return cls(p, data['source_ib_id'], data['target_ib_id'])

    def check(self, source_ib_id: str, target_ib_id: str) -> None:
        """Правило «1→1»: блокировать загрузку при несовпадении пары."""
        if source_ib_id != self.source_ib_id:
            raise ProjectError(
                f'источник {source_ib_id} не совпадает с привязанным {self.source_ib_id}: '
                'в один приёмник переносится только одна ИБ')
        if target_ib_id != self.target_ib_id:
            raise ProjectError(f'приёмник {target_ib_id} не совпадает с привязанным {self.target_ib_id}')


@dataclass
class TargetMetadata:
    """Описание структуры приёмника (словарь 'Имя' -> объект описания)."""

    objects: dict[str, dict[str, Any]]

    def find(self, obj_type: str) -> dict[str, Any] | None:
        return self.objects.get(obj_type)


def inspect_target_from_http(meta: dict[str, Any]) -> TargetMetadata:
    """Нормализация ответа /metadata в TargetMetadata."""
    objects: dict[str, dict[str, Any]] = {}
    for kind, items in (meta or {}).items():
        for it in items or []:
            name = it.get('Имя') or it.get('ИмяС')
            if name:
                objects[f'{kind}.{name}'] = it
    return TargetMetadata(objects)


def inspect_target_from_1cd(target_1cd: str | Path) -> TargetMetadata:
    """Прямое чтение 1Cv8.1CD приёмника (собственный парсер)."""
    from .source_8x_file import read_metadata  # импорт на месте: модуль в Фазе 5
    md: dict[str, Any] = read_metadata(target_1cd)
    return TargetMetadata(md['objects'])
