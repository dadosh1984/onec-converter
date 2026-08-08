"""Чтение выгрузки 8.x (1Cv8.dt) — запасной коннектор.

Формат дампа 8.x проприетарный и отличается от 7.7 (не zlib-контейнер).
Исследование — задача spike_1cv8_dt_8_x_docs_format_8x_md (низкий приоритет:
основной формат источника 8.x — живая база 1Cv8.1CD).
"""

from __future__ import annotations

from pathlib import Path


class DtFormatError(Exception):
    """Ошибка формата 1Cv8.dt."""


def open_dt(dt_path: str | Path) -> object:
    """Открыть выгрузку 8.x (пока не реализовано — исследование не завершено)."""
    raise DtFormatError('формат 1Cv8.dt не исследован (см. docs/format-8x.md); '
                        'используйте файловую ИБ 1Cv8.1CD')
