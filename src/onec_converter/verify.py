"""Финальная верификация переноса: сверка «источник ↔ приёмник».

100% полнота: каждый объект источника найден в приёмнике, количество совпадает,
контрольные суммы атрибутов совпадают. Расхождения — в отчёте.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .intermediate import OBJ_ATTRS, OBJ_KEY, OBJ_TYPE


def checksum(obj: dict[str, Any]) -> str:
    """Контрольная сумма объекта (по ключу и атрибутам)."""
    h = hashlib.sha256()
    h.update(str(obj[OBJ_TYPE]).encode('utf-8'))
    h.update('|'.join(str(k) for k in obj[OBJ_KEY]).encode('utf-8'))
    h.update(json.dumps(obj[OBJ_ATTRS], ensure_ascii=False, sort_keys=True).encode('utf-8'))
    return h.hexdigest()


@dataclass
class VerifyReport:
    total_source: int = 0
    total_target: int = 0
    matched: int = 0
    mismatched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def full(self) -> bool:
        return (self.total_source == self.total_target == self.matched
                and not self.mismatched and not self.missing)


def verify(source_objects: Iterable[dict[str, Any]],
           target_objects: Iterable[dict[str, Any]]) -> VerifyReport:
    """Сверка полноты: каждый объект источника должен быть в приёмнике.

    target_objects: те же объекты, прочитанные из приёмника (после load).
    """
    report = VerifyReport()
    src = list(source_objects)
    report.total_source = len(src)
    src_map = {(o[OBJ_TYPE], tuple(str(k) for k in o[OBJ_KEY])): o for o in src}

    tgt = list(target_objects)
    report.total_target = len(tgt)
    tgt_map = {(o[OBJ_TYPE], tuple(str(k) for k in o[OBJ_KEY])): o for o in tgt}

    for key, o in src_map.items():
        t = tgt_map.get(key)
        if t is None:
            report.missing.append(f'{key[0]}:{key[1]}')
            continue
        if checksum(o) == checksum(t):
            report.matched += 1
        else:
            report.mismatched.append(f'{key[0]}:{key[1]} (атрибуты различаются)')
    return report
