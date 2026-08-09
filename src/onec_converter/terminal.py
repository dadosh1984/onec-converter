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
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any


def is_tty(stream: Any | None = None) -> bool:
    """Вывод идёт в интерактивный терминал (а не в pipe/файл).

    CLI печатает человек-читаемые ASCII-таблицы только в TTY; при перенаправ-
    лении (| файл) оставляет JSON/CSV для машинного потребления (аудит
    раунда 6, F1)."""
    stream = stream if stream is not None else sys.stdout
    file = getattr(stream, 'isatty', None)
    return bool(file and file())


def render_table(headers: Sequence[str],
                 rows: Sequence[Sequence[object]], *, max_col: int = 40) -> str:
    """Простая человек-читаемая ASCII-таблица для CLI (без внешних зависи-
    мостей). Значения длиннее max_col обрезаются с многоточием. Возвращает
    строку с рамками, готовую к print()."""
    def _cell(v: object) -> str:
        s = str(v) if v is not None else ''
        s = ' '.join(s.split())  # схлопнуть пробелы/переводы строк
        return s if len(s) <= max_col else s[:max_col - 1] + '…'

    cells = [[_cell(h) for h in headers], *[[_cell(c) for c in r] for r in rows]]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    # де-факто: если таблица шире терминала — не падаем, рамка просто шире
    def _fmt(row: Sequence[str], sep: str = ' │ ') -> str:
        return sep.join(c.ljust(widths[i]) for i, c in enumerate(row))

    border = '─' * (sum(widths) + 2 * (len(headers) - 1) + 2)
    lines = ['┌' + border + '┐', '│ ' + _fmt(cells[0]) + ' │',
             '├' + border + '┤']
    for row in cells[1:]:
        lines.append('│ ' + _fmt(row) + ' │')
    lines.append('└' + border + '┘')
    return '\n'.join(lines)


def _stamp() -> str:
    return datetime.now(UTC).strftime('%H:%M:%S')


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
