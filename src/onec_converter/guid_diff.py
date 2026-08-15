"""Сравнение ИБ по GUID (, .

Проверка полноты переноса на уровне стабильных идентификаторов: GUID объекта
конфигурации и GUID таблицы (из DBNames) не меняются при переименованиях,
в отличие от имён. Для пары баз (источник/приёмник) строим отчёт:

- объекты конфигурации: только-в-источнике / только-в-приёмнике / общие
  с расхождением имени или типа (kind);
- таблицы по GUID (read_dbnames): только-в-источнике / только-в-приёмнике /
  общие.

`full == True` — каждый GUID источника присутствует в приёмнике и нет
расхождений имён/типов (перенос структуры завершён).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .source_8x_file import Database1CD, read_metadata


def _ib_file(d: str | Path) -> Path:
    """Путь к файлу базы: каталог ИБ или сам 1Cv8.1CD."""
    p = Path(d)
    if p.is_file() and p.name.lower() == '1cv8.1cd':
        return p
    return p / '1Cv8.1CD'


def _objects(path: str | Path) -> dict[str, dict[str, str]]:
    """Объекты конфигурации: GUID -> {kind, name, table}."""
    md = read_metadata(_ib_file(path))
    out: dict[str, dict[str, str]] = {}
    for o in md.get('objects', []):
        g = o.get('guid')
        if g:
            out[g] = {'kind': o.get('kind', ''), 'name': o.get('name', ''),
                      'table': o.get('table', '')}
    return out


def _tables(path: str | Path) -> dict[str, tuple[str, int]]:
    """Таблицы: GUID -> (kind, номер) из DBNames."""
    with Database1CD(_ib_file(path)) as db:
        return db.read_dbnames()


def guid_diff(source_dir: str | Path, target_dir: str | Path) -> dict[str, Any]:
    """Сверка двух баз по GUID: объекты конфигурации и таблицы.

    Возвращает JSON-совместимый отчёт (см. докстринг модуля).
    """
    src_objs = _objects(source_dir)
    tgt_objs = _objects(target_dir)
    src_tabs = _tables(source_dir)
    tgt_tabs = _tables(target_dir)

    only_source_objs = [{'guid': g, **o}
                        for g, o in sorted(src_objs.items()) if g not in tgt_objs]
    only_target_objs = [{'guid': g, **o}
                        for g, o in sorted(tgt_objs.items()) if g not in src_objs]
    name_mismatch: list[dict[str, str]] = []
    for g in sorted(src_objs.keys() & tgt_objs.keys()):
        s, t = src_objs[g], tgt_objs[g]
        if s['name'] != t['name'] or s['kind'] != t['kind']:
            name_mismatch.append({'guid': g, 'source': f"{s['kind']}.{s['name']}",
                                  'target': f"{t['kind']}.{t['name']}"})

    only_source_tabs = [{'guid': g, 'kind': k, 'table': n}
                        for g, (k, n) in sorted(src_tabs.items())
                        if g not in tgt_tabs]
    only_target_tabs = [{'guid': g, 'kind': k, 'table': n}
                        for g, (k, n) in sorted(tgt_tabs.items())
                        if g not in src_tabs]

    full = (not only_source_objs and not only_target_objs
            and not name_mismatch and not only_source_tabs and not only_target_tabs)
    return {
        'ok': True,
        'source_dir': str(source_dir),
        'target_dir': str(target_dir),
        'objects': {
            'only_source': only_source_objs[:500],
            'only_target': only_target_objs[:500],
            'name_mismatch': name_mismatch[:500],
            'total_source': len(src_objs),
            'total_target': len(tgt_objs),
            'common': len(src_objs.keys() & tgt_objs.keys()),
        },
        'tables': {
            'only_source': only_source_tabs[:500],
            'only_target': only_target_tabs[:500],
            'total_source': len(src_tabs),
            'total_target': len(tgt_tabs),
            'common': len(src_tabs.keys() & tgt_tabs.keys()),
        },
        'full': full,
    }
