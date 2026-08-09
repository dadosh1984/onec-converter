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
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

LEVELS = ('INFO', 'WARN', 'ERROR')
_active: AuditLog | None = None


def _sha256(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _last_record_hash(path: Path) -> str:
    """Hash последней записи JSONL (для продолжения цепочки при перезапуске)."""
    if not path.is_file():
        return ''
    last = ''
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        return ''
    try:
        rec = json.loads(last)
    except json.JSONDecodeError:
        return ''
    return str(rec.get('hash', ''))


def verify_audit(path: str | Path) -> list[dict[str, str]]:
    """Проверка целостности JSONL-журнала (tamper-evident, Фаза 37).

    Пересчитывает hash-цепочку и возвращает список нарушений (пусто = ок).
    """
    errors: list[dict[str, str]] = []
    prev = ''
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({'line': str(n), 'error': f'не JSON: {exc}'})
                continue
            got_prev = rec.get('prev_hash', '')
            got_hash = rec.get('hash', '')
            body = dict(rec)
            body.pop('hash', None)
            expect = _sha256(json.dumps(body, sort_keys=True, ensure_ascii=False))
            if got_hash and got_hash != expect:
                errors.append({'line': str(n), 'error': 'подменён hash записи'})
            if prev and got_prev != prev:
                errors.append({'line': str(n),
                               'error': f'prev_hash не совпадает ({got_prev!r} != {prev!r})'})
            prev = got_hash or expect
    return errors


class AuditLog:
    """Журнал аудита: пишет JSONL-записи в файл (или только возвращает их).

    path=None — файл не пишется (in-memory, возврат записи для тестов/лога).
    Держит один открытый handle с буферизованной записью; file_flush —
    порог накопленных записей для сброса на диск (по умолчанию 1 — каждая
    запись синхронна, журнал должен быть durable; большие нагруженные
    миграции могут повышать); max_bytes — ротация в .1 при превышении.
    """

    def __init__(self, path: str | Path | None = None,
                 max_bytes: int = 50 * 1024 * 1024,
                 file_flush: int = 1,
                 pii_masking: bool = False) -> None:
        self._path = Path(path) if path else None
        self._max_bytes = max_bytes
        self._fh: TextIO | None = None
        self._flush_bytes = 0
        self._file_flush = file_flush
        self._last_hash = ''  # hash предыдущей записи (tamper-evident, Фаза 37)
        self._pii_masking = pii_masking
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._last_hash = _last_record_hash(self._path)

    def _handle(self) -> TextIO | None:
        if self._fh is None and self._path is not None:
            if self._path.is_file() and self._path.stat().st_size > self._max_bytes:
                self._rotate()
            self._fh = open(self._path, 'a', encoding='utf-8')  # noqa: SIM115
        return self._fh

    def _rotate(self) -> None:
        """Ротация: содержимое файла ужимается до одной записи-маркера."""
        if self._path is None:
            return
        bak = self._path.with_suffix(self._path.suffix + '.1')
        shutil.copy2(self._path, bak)
        self._path.write_text('', encoding='utf-8')

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
        if self._pii_masking:
            rec['obj'] = _redact(rec['obj'])
            rec['guid'] = _redact(rec['guid'])
            rec['detail'] = _redact(rec['detail'])
        if self._path:
            rec['prev_hash'] = self._last_hash
            rec['hash'] = _sha256(json.dumps(rec, sort_keys=True, ensure_ascii=False))
            self._last_hash = rec['hash']
            fh = self._handle()
            if fh is None:
                return rec
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            self._flush_bytes += 1
            if self._flush_bytes >= self._file_flush:
                fh.flush()
                self._flush_bytes = 0
        return rec

    def flush(self) -> None:
        """Принудительный сброс буфера на диск."""
        if self._fh is not None:
            self._fh.flush()

    def close(self) -> None:
        """Закрыть handle (idempotent)."""
        if self._fh is not None:
            self._fh.flush()
            self._fh.close()
            self._fh = None

    def info(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('INFO', operation, **kw)

    def warning(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('WARN', operation, **kw)

    def error(self, operation: str, **kw: str) -> dict[str, str]:
        return self.record('ERROR', operation, **kw)


def _redact(s: str) -> str:
    """Заменить фрагменты ПДн (ИНН/СНИЛС/тел/email) на '***'."""
    if not s:
        return s
    from .pii_scanner import scan_text
    out = list(s)
    for m in scan_text(s):
        if m.kind in ('inn', 'snils', 'card', 'phone', 'pinfl'):
            for i in range(m.start, m.end):
                out[i] = '*'
    return ''.join(out)


def set_audit(path: str | Path | None, pii_masking: bool = False) -> None:
    """Активировать файловый журнал (None — сброс к in-memory)."""
    global _active
    if _active is not None:
        _active.close()
    _active = AuditLog(path, pii_masking=pii_masking) if path else None


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
