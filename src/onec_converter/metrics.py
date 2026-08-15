"""Метрики в формате Prometheus (, лёгкая, без новых зависимостей).

Конвертирует снимок Timings в plain-text формат Prometheus (`# TYPE`/`# HELP`
+ значения) для сбора Grafana/скрейпера. Опции нет — только вывод.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cache import Cache


@dataclass
class Metrics:
    """Снимок метрик для экспорта."""

    timings: dict[str, Any] | None = None
    cache: dict[str, int] | None = None

    def render(self) -> str:
        lines: list[str] = []
        if self.timings:
            lines.append('# HELP onec_operation_ms histogram времени операции.')
            lines.append('# TYPE onec_operation_ms gauge')
            for op, st in self.timings.items():
                lab = _sanitize(op)
                lines.append(f'onec_operation_count{{op="{lab}"}} {st.get("count", 0)}')
                lines.append(f'onec_operation_total_ms{{op="{lab}"}} {st.get("total_ms", 0)}')
                lines.append(f'onec_operation_max_ms{{op="{lab}"}} {st.get("max_ms", 0)}')
        if self.cache is not None:
            lines.append('# HELP onec_cache_files число файлов и байт в кеше.')
            lines.append('# TYPE onec_cache_files gauge')
            lines.append(f'onec_cache_files {self.cache.get("files", 0)}')
            lines.append('onec_cache_bytes ' + str(self.cache.get("bytes", 0)))
        if not lines:
            lines.append('# no metrics')
        return '\n'.join(lines)


def _sanitize(op: str) -> str:
    """Prometheus-совместимые метки: только [a-zA-Z0-9_:]; прочее (кириллица) -> '_'."""
    return ''.join(c if (c.isascii() and (c.isalnum() or c in ':_')) else '_'
                   for c in op)


def collect_metrics() -> str:
    """Собрать метрики процесса (Cache) для экспорта."""
    m = Metrics(timings={}, cache=Cache().stats())
    return m.render()


def render_from_timings(timings: dict[str, Any], cache: dict[str, int]) -> str:
    """Рендер метрик из готового снимка Timings и статистики кеша."""
    return Metrics(timings=timings, cache=cache).render()
