"""Audit-логирование миграции (Фаза 25): JSONL-журнал переноса данных.

Записи: время (ISO), уровень (INFO/WARN/ERROR), операция (extract/transform/
load/clone), объект, GUID приёмника (если есть), правило, результат.
Сквозная запись из ядра (load_direct) и CLI-шагов (extract/transform);
файл задаётся CLI-флагом --audit-file или env ONEC_AUDIT_FILE (для MCP).
Формат — JSONL, пригоден для ПДн-аудита «кто/что/когда/чем».

Идея: oscript-library/logos (log4j-стиль), cpr1c/logosFor1c (сквозное
логирование). Код авторский.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

LEVELS = ('INFO', 'WARN', 'ERROR')
_active: AuditLog | None = None


class AuditLog:
    """Журнал аудита: пишет JSONL-записи в файл (или только возвращает их).

    path=None — файл не пишется (in-memory, возврат записи для тестов/лога).
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path | None:
        return self._path

    def record(self, level: str, operation: str, *, obj: str = '',
               guid: str = '', rule: str = '', result: str = '',
               detail: str = '') -> dict[str, str]:
        """Записать событие; возвращает готовую запись (для проверок)."""
        level = level.upper()
        if level not in LEVELS:
            raise ValueError(f'уровень {level} ∉ {LEVELS}')
        rec = {
            'ts': datetime.now(UTC).isoformat(timespec='seconds'),
            'level': level,
            'operation': operation,
            'obj': obj,
            'guid': guid,
            'rule': rule,
            'result': result,
            'detail': detail,
        }
        if self._path:
            with open(self._path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        return rec

    def info(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('INFO', operation, **kw)

    def warning(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('WARN', operation, **kw)

    def error(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('ERROR', operation, **kw)


def set_audit(path: str | Path | None) -> None:
    """Активировать файловый журнал (None — сброс к in-memory)."""
    global _active
    _active = AuditLog(path) if path else None


def get_audit() -> AuditLog:
    """Активный журнал (лениво создаётся in-memory, если файл не задан)."""
    global _active
    if _active is None:
        _active = AuditLog()
    return _active


def read_audit(path: str | Path) -> list[dict[str, str]]:
    """Чтение JSONL-журнала (порядок записи сохранён)."""
    out: list[dict[str, str]] = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out.append({k: str(rec.get(k, '')) for k in (
                'ts', 'level', 'operation', 'obj', 'guid', 'rule',
                'result', 'detail')})
    return out
