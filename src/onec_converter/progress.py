"""Прогресс переноса данных (Фаза 38, мониторинг).

Лёгкий трекер строк/ошибок при extract/load в единицу времени. Не пишет
файл — это чистые счётчики в памяти для экспорта в Prometheus через
`metrics` или для дашборда. Код авторский.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class WorkflowProgress:
    """Атомарный счётчик прогресса переноса."""

    rows: int = 0          # перенесено строк
    objects: int = 0       # перенесено объектов
    errors: int = 0        # ошибок
    bytes_moved: int = 0   # данных (прибл.)
    started: float = field(default_factory=time.time)

    def tick_rows(self, n: int = 1, size: int = 0) -> None:
        self.rows += n
        self.bytes_moved += size

    def tick_object(self) -> None:
        self.objects += 1

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


# глобальный трекер процесса (для CLI metrics / дашборда)
_active: WorkflowProgress | None = None


def get_progress() -> WorkflowProgress:
    global _active
    if _active is None:
        _active = WorkflowProgress()
    return _active


def reset_progress() -> None:
    global _active
    _active = None
