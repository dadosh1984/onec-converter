"""Здоровье базы 1CD: `base_health` (Фаза 27, идея OneS2Zabbix).

Сводка для мониторинга/агента: версия ИБ, число таблиц и строк, блокировки
(файлы 1Cv8.1CL / 1Cv8tmp* — признак открытой ИБ), свободное место на диске,
размер и страницы файла. Только чтение, оригинал не трогается.
Код авторский.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .source_8x_file import Database1CD

LOCK_PATTERNS = ('1Cv8.1CL', '1Cv8tmp*', '1Cv8.1Ctmp')


class HealthError(Exception):
    """Ошибка оценки здоровья базы."""


def base_health(source_dir: str | Path) -> dict[str, object]:
    """Сводка «здоровья» файловой ИБ 8.x в source_dir.

    rows — суммарное число строк по всем таблицам (table_stats);
    locks — список lock-файлов (открытая ИБ / остатки); free_bytes —
    свободное место на диске каталога; version — версия формата.
    """
    src = Path(source_dir)
    cd = src / '1Cv8.1CD'
    if not cd.is_file():
        raise HealthError(f'нет 1Cv8.1CD в {source_dir}')

    locks = sorted(
        p.name for pat in LOCK_PATTERNS for p in src.glob(pat))
    free_bytes = shutil.disk_usage(src).free

    with Database1CD(cd) as db:
        version = str(db.version)
        page_size = db.page_size
        total_pages = db.total_pages
        tables = sorted(db.tables)
        rows = sum(db.table_stats(t)[0] for t in tables)

    return {
        'ok': True,
        'version': version,
        'page_size': page_size,
        'total_pages': total_pages,
        'tables': len(tables),
        'rows': rows,
        'locks': locks,
        'errors': [],          # зарезервировано под диагностику
        'file_bytes': cd.stat().st_size,
        'free_bytes': free_bytes,
    }
