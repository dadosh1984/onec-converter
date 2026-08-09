"""Здоровье базы 1CD: `base_health` (Фаза 27, идея OneS2Zabbix).

Сводка для мониторинга/агента: версия ИБ, число таблиц и строк, блокировки
(файлы 1Cv8.1CL / 1Cv8tmp* — признак открытой ИБ), свободное место на диске,
размер и страницы файла. Только чтение, оригинал не трогается.
Код авторский.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .errors import OnecConverterError
from .source_8x_file import Database1CD

LOCK_PATTERNS = ('1Cv8.1CL', '1Cv8tmp*', '1Cv8.1Ctmp')


class HealthError(OnecConverterError):
    """Ошибка оценки здоровья базы."""


def base_health(source_dir: str | Path, include_rows: bool = False,
                sample_tables: int = 0) -> dict[str, object]:
    """Сводка «здоровья» файловой ИБ 8.x в source_dir.

    rows — суммарное число строк по таблицам (table_stats) — дорогая
    операция (читает данные); по умолчанию выключена (include_rows=False),
    т.к. health-пинг для мониторинга не должен читать гигабайты. При
    sample_tables>0 вместо всех таблиц берётся выборка — первые N по
    размеру страницы данных (оценка объёма без полного чтения).
    version — версия формата; locks — lock-файлы (открытая ИБ).
    """
    src = Path(source_dir)
    cd = src / '1Cv8.1CD'
    errors: list[str] = []
    if not cd.is_file():
        raise HealthError(f'нет 1Cv8.1CD в {source_dir}')
    if cd.stat().st_size == 0:
        errors.append('файл 1Cv8.1CD пуст (0 байт)')

    locks = sorted(
        p.name for pat in LOCK_PATTERNS for p in src.glob(pat))
    if locks:
        errors.append('ИБ открыта другой сессией: ' + ', '.join(locks))
    free_bytes = shutil.disk_usage(src).free

    with Database1CD(cd) as db:
        version = str(db.version)
        page_size = db.page_size
        total_pages = db.total_pages
        tables = sorted(db.tables)
        if include_rows:
            chosen = tables
            if sample_tables and sample_tables < len(tables):
                # по длине строки из метаданных — оценка объёма без чтения
                chosen = sorted(
                    tables,
                    key=lambda n: db.tables[n].row_length,
                    reverse=True)[:sample_tables]
            rows = sum(db.table_stats(t)[0] for t in chosen)
        else:
            rows = -1  # не вычислялось — health-пинг без чтения данных

    return {
        'ok': True,
        'version': version,
        'page_size': page_size,
        'total_pages': total_pages,
        'tables': len(tables),
        'rows': rows,
        'rows_computed': include_rows,
        'locks': locks,
        'errors': errors,      # реальная диагностика (Фаза 46): пустой файл,
                               # блокировки другой сессией
        'file_bytes': cd.stat().st_size,
        'free_bytes': free_bytes,
    }
