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
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .bridge_export import export_bridge
from .bridge_format import read_bridge


def normalize_value(v: Any) -> Any:
    """Нормализовать значение перед сравнением: числа 1==1.0, даты -> iso,
    строки — strip и пустые/None-подобные -> None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v) if isinstance(v, (int, float)) else v
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, bytes):
        try:
            v = v.decode('utf-8')
        except UnicodeDecodeError:
            return v
    if isinstance(v, str):
        s = v.strip().replace('\r', '')
        if not s or s.lower() in ('none', 'nonetype'):
            return None
        try:
            return float(s) if '.' in s or 'e' in s.lower() else int(s)
        except ValueError:
            return s
    return v


def _norm_row(cfg: Any, row: list[Any], ignore_cols: set[str]) -> list[Any]:
    """Нормализовать строку по колонкам cfg; служебные колонки -> (пропущены)."""
    out: list[Any] = []
    for c in getattr(cfg, 'columns', []):
        if c.attr in ignore_cols:
            continue
        idx = c.col_num - 1
        val = row[idx] if 0 <= idx < len(row) else None
        out.append(normalize_value(val))
    return out


def compare_code(in_cfg: Any, in_rows: list[list[Any]],
                 out_cfg: Any, out_rows: list[list[Any]],
                 key_col: str = '', ignore_cols: list[str] | None = None) -> dict[str, Any]:
    """Сравнить два моста построчно по ключевой колонке (или списку).

    Ключ — первая колонка поля поиска (по умолчанию из конфигурации) либо
    список колонок через запятую (--key 'Код,Наименование').
    ignore_cols — служебные колонки, исключаемые из сравнения.
    Возвращает {'matched', 'mismatched', 'missing', 'extra', 'diffs'};
    для 'different' diff содержит расхождения на уровне полей ('cols').
    """
    keys = [k.strip() for k in key_col.split(',') if k.strip()]
    if not keys:
        first_search = next((c.attr for c in in_cfg.columns if c.search), None)
        keys = [first_search or 'Код']
    ignore = set(ignore_cols or [])
    ki = _key_index(in_cfg, in_rows, keys)
    ko = _key_index(out_cfg, out_rows, keys)
    matched = mismatched = missing = extra = 0
    diffs: list[dict[str, Any]] = []
    for k, row_in in ki.items():
        if k not in ko:
            missing += 1
            diffs.append({'key': k, 'kind': 'missing'})
            continue
        n_in = _norm_row(in_cfg, row_in, ignore)
        n_out = _norm_row(out_cfg, ko[k], ignore)
        if n_in != n_out:
            mismatched += 1
            cols = []
            visible = [c for c in in_cfg.columns if c.attr not in ignore]
            for c, a, b in zip(visible, n_in, n_out):
                if a != b:
                    cols.append({'col': c.attr, 'in': a, 'out': b})
            diffs.append({'key': k, 'kind': 'different', 'cols': cols})
        else:
            matched += 1
    for k in ko:
        if k not in ki:
            extra += 1
            diffs.append({'key': k, 'kind': 'extra'})
    return {'matched': matched, 'mismatched': mismatched,
            'missing': missing, 'extra': extra, 'diffs': diffs,
            'ok': mismatched == 0 and missing == 0 and extra == 0}


def _key_index(cfg: Any, rows: list[list[Any]], keys: list[str]) -> dict[tuple[str, ...], list[Any]]:
    """Собрать {кортеж значений ключевых колонок: полная строка}."""
    idxs: list[int] = []
    for key in keys:
        col = next((c for c in cfg.columns if c.attr == key), None)
        idxs.append(col.col_num - 1 if col and col.col_num else -1)
    out: dict[tuple[str, ...], list[Any]] = {}
    for r in rows:
        parts: list[str] = []
        for i in idxs:
            if 0 <= i < len(r) and r[i] not in (None, ''):
                parts.append(str(r[i]))
            else:
                parts.append('')
        if any(parts):
            out[tuple(parts)] = r
    return out


def verify_roundtrip(source_dir: str | Path, copied_dir: str | Path,
                     obj_fullname: str, bridge_in: str | Path,
                     workdir: str | Path | None = None,
                     limit: int | None = None,
                     key_col: str = '',
                     ignore_cols: list[str] | None = None) -> dict[str, Any]:
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
        # limit — пилотный прогон: сверяем только первые N строк моста
        # (загруженных в копию приёмника) с первыми N строками из неё.
        if limit:
            in_rows = in_rows[:limit]
        out_cfg, out_rows = read_bridge(out_tmp)
        cmp = compare_code(in_cfg, in_rows, out_cfg, out_rows,
                           key_col, ignore_cols=ignore_cols)
        rep = {'ok': cmp['ok'], 'exported': exp.get('rows', len(out_rows)),
               'in_rows': len(in_rows), **cmp}
    finally:
        try:
            out_tmp.unlink()
        except OSError:
            pass
    return rep
