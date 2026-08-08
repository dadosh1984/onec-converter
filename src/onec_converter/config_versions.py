"""Версии конфигурации из файла базы 8.x (Фаза 11, идея E3).

В 1Cv8.1CD нет истории версий хранилища конфигуратора (она — в Конфигураторе).
Честный суррогат из самого файла:

- формат файла (`Database1CD.version`, напр. 8.3.8.0);
- версия ИБ и требуемая версия платформы (таблица IBVERSION);
- файлы конфигурации: число и даты создания/изменения в CONFIG (текущая),
  CONFIGSAVE (последнее сохранение), PARAMS (параметры);
- дифф CONFIG ↔ CONFIGSAVE по именам файлов: добавлено / удалено / изменено
  (по размеру) — «что изменилось с последнего сохранения».
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .source_8x_file import Database1CD, decode_datetime, decode_numeric, decode_nvc

_CONFIG_TABLES = ('CONFIG', 'CONFIGSAVE', 'PARAMS')


def _rows(db: Database1CD, table_name: str) -> list[tuple[str, datetime | None,
                                                          datetime | None, int]]:
    """(имя файла, создан, изменён, размер) для таблицы конфигурации."""
    t = db.tables[table_name]
    f = t.fields
    fname_f, created_f, modified_f, size_f = (f['FILENAME'], f['CREATION'],
                                              f['MODIFIED'], f['DATASIZE'])
    out: list[tuple[str, datetime | None, datetime | None, int]] = []
    for row in db.table_rows(t):
        if row[:1] == b'\x01':
            continue
        nm = decode_nvc(row[fname_f.offset:fname_f.offset + fname_f.size])
        if not nm or any(ord(c) < 32 for c in nm):
            continue
        created = decode_datetime(row[created_f.offset:created_f.offset + 7])
        modified = decode_datetime(row[modified_f.offset:modified_f.offset + 7])
        size = decode_numeric(row[size_f.offset:size_f.offset + size_f.size],
                              size_f.length, size_f.precision)
        out.append((nm, created, modified, int(size) if size else 0))
    return out


def _diff(src: list[tuple[str, datetime | None, datetime | None, int]],
          tgt: list[tuple[str, datetime | None, datetime | None, int]]) \
        -> dict[str, Any]:
    src_map = {nm: sz for nm, _, _, sz in src}
    tgt_map = {nm: sz for nm, _, _, sz in tgt}
    return {
        'added': sorted(tgt_map.keys() - src_map.keys())[:500],
        'removed': sorted(src_map.keys() - tgt_map.keys())[:500],
        'changed': sorted(nm for nm in (src_map.keys() & tgt_map.keys())
                          if src_map[nm] != tgt_map[nm])[:500],
    }


def config_versions(path: str | Path) -> dict[str, Any]:
    """Версии и сохранения конфигурации из файла базы (см. докстринг модуля)."""
    path = Path(path)
    with Database1CD(path) as db:
        files: dict[str, Any] = {}
        for tname in _CONFIG_TABLES:
            if tname not in db.tables:
                files[tname] = {'count': 0}
                continue
            rows = _rows(db, tname)
            dates = [m for _, _, m, _ in rows if m is not None]
            files[tname] = {
                'count': len(rows),
                'created_min': str(min(dates)) if dates else None,
                'created_max': str(max(dates)) if dates else None,
            }
        diff: dict[str, Any] = {}
        if {'CONFIG', 'CONFIGSAVE'} <= set(db.tables):
            diff = _diff(_rows(db, 'CONFIG'), _rows(db, 'CONFIGSAVE'))
        ibversion: list[dict[str, Any]] = []
        if 'IBVERSION' in db.tables:
            t = db.tables['IBVERSION']
            for row in db.table_rows(t):
                rec: dict[str, Any] = {}
                for fname, fd in t.fields.items():
                    raw = row[fd.offset:fd.offset + fd.size]
                    rec[fname] = decode_numeric(raw, fd.length, fd.precision)
                ibversion.append(rec)
        fmt = str(db.version)
    return {
        'ok': True,
        'source_dir': str(path),
        'format': fmt,
        'ibversion': ibversion,
        'config_files': files,
        'config_vs_configsave': diff,
    }
