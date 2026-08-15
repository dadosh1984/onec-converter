"""Техжурнал 1С как ИСТОЧНИК данных .

Чтение каталога техжурнала 1С (справочник процессов/событий) в единую
модель событий — мостик к диагностике миграции: по событиям SDBL/EXCP/
TTIMEOUT можно оценить активность и ошибки платформы до и после переноса.

Формат строки (подтверждён разбором реальных логов, см. docs/format-8x.md,
раздел «Техжурнал»):

    YYYYMMddHHmmss.mmm-<длительность мс>-<уровень>|
    <процесс>,<направленность 0|1>,<контекст>,<событие>,<уровень>|
    <поле>=<значение>|...

Код авторский (идея: Polyplastic/1c-parsing-tech-log).
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from .audit import get_audit

_HEAD = re.compile(
    r'^(\d{8}\d{6}\.\d{3})-(\d+)-(\d)\|'
    r'([^,]*),([01]),([^,]*),([^,]*),(\d)\|(.*)$'
)


class TechLogError(Exception):
    """Ошибка чтения техжурнала."""


def parse_techlog_line(line: str) -> dict[str, object] | None:
    """Разобрать одну строку техжурнала -> событие (None для мусора)."""
    m = _HEAD.match(line.rstrip('\r\n'))
    if not m:
        return None
    ts_raw, dur, lvl, process, direction, ctx, event, level2, rest = m.groups()
    try:
        ts = datetime.strptime(ts_raw, '%Y%m%d%H%M%S.%f').replace(
            tzinfo=UTC).isoformat()
    except ValueError:
        return None
    fields: dict[str, str] = {}
    for kv in rest.split('|'):
        if not kv:
            continue
        k, _, v = kv.partition('=')
        fields[k.strip()] = v.strip()
    return {
        'ts': ts,
        'duration_ms': int(dur),
        'level': int(lvl),
        'process': process,
        'direction': int(direction),
        'context': ctx,
        'event': event,
        'level2': int(level2),
        'fields': fields,
    }


class TechLog:
    """Каталог техжурнала: файлы *.log (и *.lgp) как источник событий."""

    def __init__(self, log_dir: str | Path):
        self.dir = Path(log_dir)
        if not self.dir.is_dir():
            raise TechLogError(f'каталог техжурнала не существует: {log_dir}')

    def files(self) -> list[Path]:
        return sorted(self.dir.glob('*.log*'))

    def iter_events(self, process: str = '', event: str = '',
                    level_min: int = 0, tail: int = 0) -> Iterator[dict[str, object]]:
        """События с фильтрами: процесс (подстрока), событие, уровень >=,
        tail — только последние N (по всему набору)."""
        buf: list[dict[str, object]] = []
        for f in self.files():
            with open(f, encoding='utf-8', errors='replace') as fh:
                for raw in fh:
                    rec = parse_techlog_line(raw)
                    if rec is None:
                        continue
                    if process and process not in str(rec['process']):
                        continue
                    if event and str(rec['event']) != event:
                        continue
                    if int(str(rec['level'])) < level_min:
                        continue
                    if tail:
                        buf.append(rec)
                    else:
                        yield rec
        if tail:
            yield from buf[-tail:]

    def read_events(self, process: str = '', event: str = '',
                    level_min: int = 0, tail: int = 0,
                    out_file: str = '') -> dict[str, object]:
        """События списком; out_file — запись JSON рядом (опционально).
        Журнал аудита: INFO-событие techlog."""
        events = list(self.iter_events(process, event, level_min, tail))
        if out_file:
            Path(out_file).write_text(
                json.dumps(events, ensure_ascii=False, indent=1),
                encoding='utf-8')
        get_audit().info('techlog', obj=str(self.dir),
                         result='ok', detail=str(len(events)))
        return {'ok': True, 'count': len(events), 'events': events,
                'files': [str(p) for p in self.files()]}
