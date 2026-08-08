"""Журнал метрик времени операций парсинга (идея A3).

Аналог «Оценки производительности» БСП / 1C_PrometheusExporter: histogram
времени выполнения операций в разрезе ключевых операций. Здесь — простой
накопитель: операция (например `read_metadata:Справочник`) -> счётчик,
суммарные мс, максимум. Снимок отдаётся в status-тул MCP.

Не потокобезопасен (пайплайн однопоточный) и живёт в процессе; для
персистентности используйте `snapshot()`.
"""

from __future__ import annotations

from typing import Any

_ENTRY = '_total'


class Timings:
    """Накопитель метрик: op -> {count, total_ms, max_ms}."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, float | int]] = {}

    def record(self, op: str, ms: float) -> None:
        """Зафиксировать длительность операции (мс)."""
        e = self._data.get(op)
        if e is None:
            self._data[op] = {'count': 1, 'total_ms': ms, 'max_ms': ms}
        else:
            e['count'] = int(e['count']) + 1
            e['total_ms'] = float(e['total_ms']) + ms
            if ms > float(e['max_ms']):
                e['max_ms'] = ms

    def op(self, op: str, ms: float) -> None:
        """Замер по конкретной операции (совместимая запись)."""
        self.record(op, ms)

    def snapshot(self) -> dict[str, Any]:
        """Снимок: op -> {count, total_ms, avg_ms, max_ms}."""
        out: dict[str, Any] = {}
        for op, e in self._data.items():
            n = int(e['count'])
            total = float(e['total_ms'])
            out[op] = {
                'count': n,
                'total_ms': round(total, 1),
                'avg_ms': round(total / n, 1) if n else 0.0,
                'max_ms': round(float(e['max_ms']), 1),
            }
        return out

    def __len__(self) -> int:
        return len(self._data)


# глобальный журнал процесса (как в БСП — одна точка записи)
GLOBAL = Timings()
