"""Обратный контроль переноса (round-trip приёмника).

После импорта моста в КОПИЮ приёмника выполняется обратная выгрузка данных
из копии в xlsx-мост (той же командой export_bridge) и поштучное сравнение
строк с исходным мостом по всем колонкам (не только по полям поиска).

Цель — 100% уверенность, что каждый перенесённый реквизит записан корректно,
а не только найден ключ поиска (кода достаточно для find-or-create, но не для
контроля значений прочих колонок).
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .bridge_export import export_bridge
from .bridge_format import read_bridge


def compare_code(in_cfg: Any, in_rows: list[list[Any]],
                 out_cfg: Any, out_rows: list[list[Any]],
                 key_col: str = '') -> dict[str, Any]:
    """Сравнить два моста построчно по ключевой колонке.

    Ключ — первая колонка поля поиска (по умолчанию из конфигурации).
    Возвращает {'matched', 'mismatched', 'missing', 'extra', 'diffs'}.
    """
    key = key_col or next((c.attr for c in in_cfg.columns if c.search), None)
    if key is None:
        key = 'Код'
    ki = _key_index(in_cfg, in_rows, key)
    ko = _key_index(out_cfg, out_rows, key)
    matched = mismatched = missing = extra = 0
    diffs: list[dict[str, Any]] = []
    for k, row_in in ki.items():
        if k not in ko:
            missing += 1
            diffs.append({'key': k, 'kind': 'missing'})
            continue
        if row_in != ko[k]:
            mismatched += 1
            diffs.append({'key': k, 'kind': 'different',
                          'in': row_in, 'out': ko[k]})
        else:
            matched += 1
    for k in ko:
        if k not in ki:
            extra += 1
            diffs.append({'key': k, 'kind': 'extra'})
    return {'matched': matched, 'mismatched': mismatched,
            'missing': missing, 'extra': extra, 'diffs': diffs,
            'ok': mismatched == 0 and missing == 0 and extra == 0}


def _key_index(cfg: Any, rows: list[list[Any]], key: str) -> dict[str, Any]:
    """Безопасно собрать {значение ключа: полная строка как список}."""
    ki_c = next((c for c in cfg.columns if c.attr == key), None)
    out: dict[str, Any] = {}
    if ki_c is None or not ki_c.col_num:
        return out
    for r in rows:
        idx = ki_c.col_num - 1
        if 0 <= idx < len(r) and r[idx] not in (None, ''):
            out[str(r[idx])] = r
    return out


def verify_roundtrip(source_dir: str | Path, copied_dir: str | Path,
                     obj_fullname: str, bridge_in: str | Path,
                     workdir: str | Path | None = None,
                     limit: int | None = None,
                     key_col: str = '') -> dict[str, Any]:
    """Выгрузить данные обратно из КОПИИ приёмника и сравнить с исходным мостом.

    source_dir — копия приёмника (каталог с 1Cv8.1CD после импорта);
    copied_dir — НЕ используется напрямую (оставлен для совместимости),
    читается сама копия source_dir; bridge_in — исходный мост.
    """
    rep: dict[str, Any] = {'ok': False}
    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        rep['error'] = f'нет файла приёмника: {cd}'
        return rep
    if workdir is None:
        workdir = source_dir
    wd = Path(workdir)
    wd.mkdir(parents=True, exist_ok=True)
    out_tmp = Path(tempfile.mkstemp(suffix='.xlsx', dir=wd)[1])
    try:
        exp = export_bridge(source_dir, obj_fullname, out_tmp, limit=limit or 0)
        in_cfg, in_rows = read_bridge(bridge_in)
        out_cfg, out_rows = read_bridge(out_tmp)
        cmp = compare_code(in_cfg, in_rows, out_cfg, out_rows, key_col)
        rep = {'ok': cmp['ok'], 'exported': exp.get('rows', len(out_rows)),
               'in_rows': len(in_rows), **cmp}
    finally:
        try:
            out_tmp.unlink()
        except OSError:
            pass
    return rep
