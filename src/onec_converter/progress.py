"""Прогресс переноса данных (, мониторинг).

Лёгкий трекер строк/ошибок при extract/load в единицу времени. Не пишет
файл — это чистые счётчики в памяти для экспорта в Prometheus через
`metrics` или для дашборда. Код авторский.

Плюс визуальный progress-бар в терминале (stderr, не ломает JSON stdout):
`TermProgress` рисует процент, число перенесённых объектов и текущую таблицу,
а по завершении — сводку таблиц приёмника.
"""
from __future__ import annotations

import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import Any, TextIO


@dataclass
class WorkflowProgress:
    """Атомарный счётчик прогресса переноса."""

    rows: int = 0          # перенесено строк
    objects: int = 0       # перенесено объектов
    errors: int = 0        # ошибок
    bytes_moved: int = 0   # данных (прибл.)
    total: int = 0         # ожидаемый объём (единиц work)
    started: float = field(default_factory=time.time)

    def tick_rows(self, n: int = 1, size: int = 0) -> None:
        self.rows += n
        self.bytes_moved += size

    def tick_object(self) -> None:
        self.objects += 1

    def log(self, msg: str) -> None:
        """Прогресс-сообщение (stderr — stdout остаётся машиночитаемым)."""
        import sys

        print(f'[progress {self.elapsed():.1f}s] {msg}', file=sys.stderr)

    def tick_error(self) -> None:
        self.errors += 1

    def elapsed(self) -> float:
        return max(time.time() - self.started, 1e-9)

    def rows_per_sec(self) -> float:
        return self.rows / self.elapsed()

    def snapshot(self) -> dict[str, float]:
        return {
            'rows': float(self.rows),
            'objects': float(self.objects),
            'errors': float(self.errors),
            'bytes_moved': float(self.bytes_moved),
            'rows_per_sec': self.rows_per_sec(),
            'elapsed_s': round(self.elapsed(), 3),
        }

    def render_prometheus(self) -> str:
        s = self.snapshot()
        lines = [
            '# HELP onec_progress_rows строк обработано',
            '# TYPE onec_progress_rows counter',
            f'onec_progress_rows {s["rows"]:.0f}',
            '# HELP onec_progress_objects объекты обработано',
            '# TYPE onec_progress_objects counter',
            f'onec_progress_objects {s["objects"]:.0f}',
            '# HELP onec_progress_errors ошибки',
            '# TYPE onec_progress_errors counter',
            f'onec_progress_errors {s["errors"]:.0f}',
            '# HELP onec_progress_bytes_moved данные перемещены',
            '# TYPE onec_progress_bytes_moved counter',
            f'onec_progress_bytes_moved {s["bytes_moved"]:.0f}',
            '# HELP onec_progress_rows_per_sec скорость',
            '# TYPE onec_progress_rows_per_sec gauge',
            f'onec_progress_rows_per_sec {s["rows_per_sec"]:.2f}',
        ]
        return '\n'.join(lines)


def get_progress() -> WorkflowProgress | None:
    """Активный прогресс текущего контекста.

    В текущей реализации всегда None — глобальный трекер удалён.
    Для отслеживания прогресса создавайте WorkflowProgress явно.
    """
    return None


def reset_progress() -> None:
    """Сброс прогресса (больше не нужен — глобал удалён)."""


# ---------------------------------------------------------------------------
# Визуальный progress-бар переноса (stderr)
# ---------------------------------------------------------------------------

_BAR_WIDTH = 32
_EMOJI = {'Справочник': '📚', 'Документ': '📄', 'РегистрСведений': '🗂️',
          'РегистрНакопления': '📊', 'РегистрБухгалтерии': '🧮',
          'Перечисление': '🏷️', 'ПланСчетов': '🧾', 'Таблица': '📦'}


def _tty(out: TextIO) -> bool:
    return bool(getattr(out, 'isatty', lambda: False)())


class TermProgress:
    """Прогресс переноса: объекты, таблицы, процент.

    draw() вызывается после каждого пакета(объекта). Учитывается stderr
    и TTY/последовательный вывод. В не-TTY выводится компактная строка,
    в TTY — перезаписывается \\r.
    """

    def __init__(self, total: int, out: TextIO | None = None):
        self.total = max(total, 1)
        self.done = 0
        self.tables: dict[str, int] = {}
        self._out = out or sys.stderr
        self._tty = _tty(self._out)
        self._width = _bar_width()
        self._last_decile = -1

    def update(self, obj_type: str = '', table: str = '', rows: int = 1) -> None:
        """Сообщить о переносе N записей (по умолчанию 1) в таблицу."""
        if table:
            self.tables[table] = self.tables.get(table, 0) + rows
        self.done += rows

    def _kind_of(self, obj_type: str) -> str:
        return (obj_type.split('.', 1)[0] if obj_type else 'Таблица')

    def _bar(self, pct: int) -> str:
        filled = round(pct / 100 * self._width)
        return '█' * filled + '░' * (self._width - filled)

    def draw(self, obj_type: str = '', table: str = '') -> None:
        pct = self.done * 100 // self.total
        if self._tty:
            bar = self._bar(pct)
            kind_icon = _EMOJI.get(self._kind_of(obj_type), '')
            line = (f'\r{kind_icon} {bar} {pct:3d}% '
                    f'{self.done}/{self.total} '
                    f'[{table or obj_type or ""}]')
            self._out.write(line + '\x1b[K')
            self._out.flush()
        else:
            # вне TTY — редкие узлы прогресса: старт, каждая новая 10%-плитка, финал
            decile = pct // 10 if pct >= 10 else 0
            is_new_decile = decile != self._last_decile
            if self.done == 1:
                self._out.write(f'[onec-converter] перенос: 0% ({self.done}/{self.total}) '
                                f'[{table or obj_type or ""}]\n')
            elif self.done == self.total or (is_new_decile and pct >= 10):
                self._out.write(f'[onec-converter] перенос: {pct}% '
                                f'({self.done}/{self.total}) '
                                f'[{table or obj_type or ""}]\n')
            if is_new_decile:
                self._last_decile = decile
            self._out.flush()

    def finish(self, report: dict[str, Any] | None = None, ok: bool = True) -> None:
        if self._tty:
            self._out.write('\r' + ' ' * 100 + '\r')
        for table, n in sorted(self.tables.items(), key=lambda i: -i[1]):
            self._out.write(f'  {table}: {n} записей\n')
        status = '✓ перенос завершён' if ok else '✘ перенос прерван'
        self._out.write(f'{status}\n')
        if report is not None:
            self._out.write(f'  итого: {report.get("total", self.done)} объектов'
                            f', tables={len(self.tables)}\n')
        self._out.flush()


def _bar_width() -> int:
    try:
        return max(shutil.get_terminal_size((80, 24)).columns // 3, 20)
    except Exception:  # noqa: BLE001 — негарантированный терминал
        return _BAR_WIDTH
