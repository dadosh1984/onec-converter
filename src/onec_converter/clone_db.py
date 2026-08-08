"""Полный сценарий копии базы: `clone-db` (Фаза 24).

Полная копия структуры+данных файловой ИБ 8.x в новый каталог (файл
1Cv8.1CD целиком) с кеш-сбросом по новому ключу; опционально — копия
правил маппинга рядом (сценарий «стенд»: база + правила для повторного
прогона без влияния на оригинал).

Идеи: arkuznetsov/cpdb (копирование базы+MSSQL), Tavalik/Perezalivator
(перезаливка). Код авторский.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .cache import Cache, file_key


class CloneError(Exception):
    """Ошибка клонирования базы."""


def clone_db(source_dir: str | Path, target_dir: str | Path,
             rules: str | Path = '') -> dict[str, object]:
    """Полная копия файловой ИБ 8.x (1Cv8.1CD) в новый каталог.

    source_dir — каталог с 1Cv8.1CD (оригинал read-only, не трогается);
    target_dir — каталог приёмника (создаётся); rules — файл правил
    маппинга TOON, копируется в target_dir/rules/ (опция --with-rules,
    сценарий «стенд»). Кеш метаданных по новому пути инвалидируется.
    Возвращает {ok, source, target, bytes, tables, rules}.
    """
    src = Path(source_dir)
    cd = src / '1Cv8.1CD'
    if not cd.is_file():
        raise CloneError(f'нет 1Cv8.1CD в {source_dir}')

    tgt = Path(target_dir)
    tgt.mkdir(parents=True, exist_ok=True)
    dst = tgt / '1Cv8.1CD'
    if dst.resolve() == cd.resolve():
        raise CloneError('source_dir == target_dir: клонирование в себя')

    # кеш-сброс: вычисляем ключ ПРЕЖНЕГО файла приёмника (если он был)
    # и дропаем именно его — после копии новый dst получит новый ключ
    # (новый mtime), которого в кеше ещё нет; старый кеш недействителен.
    cache = Cache()
    if dst.is_file():
        cache.drop(file_key(dst))

    # полная копия файла (структура + данные), оригинал не изменяется
    shutil.copy2(cd, dst)

    from .source_8x_file import Database1CD

    with Database1CD(dst) as db:
        tables = len(db.tables)

    rules_path: str | None = None
    if rules:
        rp = Path(rules)
        if not rp.is_file():
            raise CloneError(f'нет файла правил: {rules}')
        rules_dir = tgt / 'rules'
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_dst = rules_dir / rp.name
        shutil.copy2(rp, rules_dst)
        rules_path = str(rules_dst)

    return {
        'ok': True,
        'source': str(cd),
        'target': str(dst),
        'bytes': dst.stat().st_size,
        'tables': tables,
        'rules': rules_path,
    }
