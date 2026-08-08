"""Видимость команд MCP-сервера в терминале пользователя.

MCP работает по stdio-протоколу: stdout занят JSON-RPC, поэтому
человекочитаемые события пишутся в **stderr** — они видны в терминале,
где запущен сервер (python -m onec_converter.mcp_server), и в TUI
MCP-клиентов (pi/Claude), которые показывают stderr процесса.

Каждое применение команды onec-converter логируется как:
    [onec-converter 17:31:02] ▶ table_sizes(1C_8.1, 'Reference')
    [onec-converter 17:31:02] ✔ table_sizes — 300 таблиц (62 ms)
    [onec-converter 17:31:03] ✘ query_table — таблица не найдена: _XXX
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from typing import Any


def _stamp() -> str:
    return datetime.now().strftime('%H:%M:%S')


def _emit(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


def tool_started(name: str, args_repr: str) -> None:
    """Начало применения команды MCP-сервера (видно в терминале)."""
    _emit(f'[onec-converter {_stamp()}] ▶ {name}({args_repr})')


def tool_finished(name: str, ok: bool, ms: float, summary: str = '') -> None:
    """Итог применения команды: ok/ошибка + время + краткое резюме."""
    mark = '✔' if ok else '✘'
    extra = f' — {summary}' if summary else ''
    _emit(f'[onec-converter {_stamp()}] {mark} {name} ({ms:.0f} ms){extra}')


def tool_error(name: str, ms: float, error: str) -> None:
    """Ошибка применения команды."""
    _emit(f'[onec-converter {_stamp()}] ✘ {name} ({ms:.0f} ms) — {error}')


def playbook_step(n: int, total: int, step: str) -> None:
    """Служебное сообщение фазы плейбука (не результат команды)."""
    _emit(f'[onec-converter {_stamp()}] ─── шаг {n}/{total}: {step}')


def tool_summary(result: Any) -> str:
    """Краткое резюме результата JSON-тула для терминала."""
    if isinstance(result, str):
        try:
            data: Any = __import__('json').loads(result)
        except (ValueError, TypeError):
            data = result
    else:
        data = result
    if isinstance(data, dict):
        parts: list[str] = []
        for key in ('ok', 'count', 'objects', 'total', 'created',
                    'only_source', 'only_target', 'cached'):
            if key in data:
                parts.append(f'{key}={data[key]}')
        if not parts:
            parts.append(str(data)[:80])
        return ', '.join(parts)[:160]
    return str(data)[:160]


def now_ms() -> float:
    """Текущее время в миллисекундах (для замеров)."""
    return time.perf_counter() * 1000
