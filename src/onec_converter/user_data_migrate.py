"""Оркестратор переноса «пользовательские данные через xlsx-мост».

Простой путь, минимум команд поверх существующих:
  check_paths -> clone_db (копия приёмника) -> build_plan (только user)
  -> export_sections (xlsx-мост по разделу) -> load_and_verify (загрузка
  + обратный тест по одному файлу, цикл до совпадения).

Источник всегда read-only; запись только в копию приёмника в workdir.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .bridge_export import export_bridge
from .bridge_verify import verify_roundtrip
from .classify import build_plan
from .clone_db import clone_db
from .epf_load import import_bridge
from .source_8x_file import read_metadata


class MigrateError(Exception):
    """Ошибка переноса пользовательских данных."""


def check_paths(source_dir: str | Path, target_dir: str | Path) -> dict[str, Any]:
    """Проверить пути: оба каталога существуют, оба содержат 1Cv8.1CD,
    каталоги не совпадают."""
    src = Path(source_dir)
    tgt = Path(target_dir)
    if not (src / '1Cv8.1CD').is_file():
        return {'ok': False, 'error': f'нет 1Cv8.1CD в источнике: {src}'}
    if not (tgt / '1Cv8.1CD').is_file():
        return {'ok': False, 'error': f'нет 1Cv8.1CD в приёмнике: {tgt}'}
    if src.resolve() == tgt.resolve():
        return {'ok': False, 'error': 'каталоги источника и приёмника — одна и та же ИБ'}
    return {'ok': True, 'source': str(src), 'target': str(tgt)}


def export_sections(source_dir: str | Path, plan: list[dict[str, str]],
                    out_dir: str | Path) -> list[Path]:
    """Выгрузить каждый раздел плана в отдельный xlsx-мост; вернуть пути файлов."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for item in plan:
        target = out / item['file']
        rep = export_bridge(source_dir, item['name'], target)
        if not rep.get('ok'):
            raise MigrateError(
                f'экспорт раздела {item["name"]} не удался: {rep.get("error")}')
        files.append(target)
    return files


def load_and_verify(bridge_path: str | Path, target_dir: str | Path,
                    obj_fullname: str = '',
                    workdir: str | Path | None = None,
                    key_col: str = '', ignore_cols: list[str] | None = None,
                    max_tries: int = 3,
                    pilot_rows: int = 3) -> dict[str, Any]:
    """Загрузить один мост в копию приёмника и прогнать обратный тест.

    Пилотный прогон: сначала загружаются первые pilot_rows строк моста и
    сверяются обратным тестом (limit=pilot_rows); если пилот ок — загрузка
    всех строк и полная сверка. Цикл повторяется до ok=True (не более
    max_tries раз); расхождения фиксируются в отчёте.
    """
    attempts = 0
    imp: dict[str, Any] = {}
    pilot: dict[str, Any] = {'ok': False}
    while attempts < max_tries:
        attempts += 1
        # пилот: 2-3 позиции сначала, полный перенос — только после их сверки
        imp = import_bridge(bridge_path, target_dir, workdir=workdir,
                            max_rows=pilot_rows or None)
        if not imp.get('ok'):
            return {'ok': False, 'attempt': attempts,
                    'error': imp.get('error', 'импорт не удался')}
        # данные записаны в КОПИЮ (work.1CD) — верифицируем именно её каталог
        copied = Path(imp['copy_path']).parent
        if pilot_rows:
            pilot = verify_roundtrip(copied, copied, obj_fullname,
                                     bridge_path, workdir=copied,
                                     limit=pilot_rows, key_col=key_col,
                                     ignore_cols=ignore_cols)
            if not pilot.get('ok'):
                return {'ok': False, 'attempt': attempts, 'pilot': pilot,
                        'error': 'пилотная сверка не совпала — полная загрузка не выполнена'}
        imp = import_bridge(bridge_path, target_dir, workdir=workdir)
        if not imp.get('ok'):
            return {'ok': False, 'attempt': attempts,
                    'error': imp.get('error', 'импорт не удался')}
        ver = verify_roundtrip(copied, copied, obj_fullname,
                               bridge_path, workdir=copied, key_col=key_col,
                               ignore_cols=ignore_cols)
        if ver.get('ok'):
            return {'ok': True, 'attempt': attempts, 'pilot': pilot,
                    'imported': imp, 'verify': ver}
    return {'ok': False, 'attempt': attempts, 'pilot': pilot,
            'imported': imp, 'verify': ver}


def run_migration(source_dir: str | Path, target_dir: str | Path,
                  workdir: str | Path | None = None,
                  objects: str = '',
                  meta: dict[str, Any] | None = None,
                  key_col: str = '',
                  ignore_cols: list[str] | None = None,
                  pilot_rows: int = 3) -> dict[str, Any]:
    """Полный цикл переноса пользовательских данных:
    пути -> копия приёмника -> план -> экспорт мостов -> загрузка+обратный тест."""
    rep = check_paths(source_dir, target_dir)
    if not rep['ok']:
        return rep
    src = Path(source_dir)
    wd = Path(workdir) if workdir else Path.cwd() / 'workdir'
    wd.mkdir(parents=True, exist_ok=True)
    target_copy = wd / 'target_copy'
    if not (target_copy / '1Cv8.1CD').is_file():
        clone_db(target_dir, target_copy)

    md = meta if meta is not None else read_metadata(src / '1Cv8.1CD')
    plan = build_plan(md)
    if objects:
        wanted = {o.strip() for o in objects.split(',')}
        plan = [p for p in plan if p['name'] in wanted]

    bridges_dir = wd / 'bridges'
    files = export_sections(src, plan, bridges_dir)

    results: dict[str, Any] = {}
    for bridge, item in zip(files, plan):
        results[item['name']] = load_and_verify(
            bridge, target_copy, obj_fullname=item['name'],
            workdir=wd / 'tmp', key_col=key_col, ignore_cols=ignore_cols,
            pilot_rows=pilot_rows)

    ok = all(r.get('ok') for r in results.values())
    return {'ok': ok, 'source': str(src), 'target_copy': str(target_copy),
            'plan': plan, 'exported': len(files),
            'sections': results}
