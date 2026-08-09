"""AI-навыки (детерминированные, без внешних LLM), Фаза 40.

Авто-маппинг схем, объяснение расхождений и сжатие метаданных — всё на
чистых эвристиках/нормализации имён (без сетевых вызовов), чтобы LLM-агент
получал готовые, проверяемые структуры, а не галлюцинировал о полях. Код
авторский.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .enum_mapper import normalize_enum_name


def _norm_field(name: str) -> str:
    return normalize_enum_name(name)


def auto_map_schemas(source_meta: dict[str, Any],
                     target_meta: dict[str, Any]) -> dict[str, Any]:
    """Авто-маппинг объектов и реквизитов по нормализованным именам/синонимам.

    source_meta/target_meta — словари read_metadata ({objects: [...]}).
    Возвращает {ok, rules:[{source,target,attributes}], matched, unmatched}.
    """
    rules = []
    matched = 0
    for o in source_meta['objects']:
        sname = f"{o['kind']}.{o['name']}"
        # найти целевой объект по kind + нормализованному имени или синониму
        tnorm_base = _norm_field(o['name'])
        snorm = _norm_field(o.get('synonym') or '')
        target_obj = None
        for t in target_meta['objects']:
            if t['kind'] != o['kind']:
                continue
            if (_norm_field(t['name']) == tnorm_base or
                    (snorm and _norm_field(t.get('synonym') or '') == snorm)):
                target_obj = t
                break
        if target_obj is None:
            continue
        tgt_attrs = {a['name']: a for a in (target_obj.get('attributes') or [])}
        tgt_norm = {_norm_field(n): n for n in tgt_attrs}
        mapping: dict[str, str] = {}
        for src_a in (o.get('attributes') or []):
            direct = tgt_attrs.get(src_a['name'])
            if direct is not None:
                mapping[src_a['name']] = src_a['name']
                continue
            norm = tgt_norm.get(_norm_field(src_a['name']))
            if norm:
                mapping[src_a['name']] = norm
        rules.append({'source': sname,
                      'target': f"{target_obj['kind']}.{target_obj['name']}",
                      'attributes': mapping,
                      # уверенность сопоставления: exact — по нормализованному
                      # имени, synonym — по синониму (требует подтверждения)
                      'confidence': ('exact' if
                                     _norm_field(target_obj['name']) == tnorm_base
                                     else 'synonym')})
        matched += 1
    return {'ok': True, 'rules': rules, 'matched': matched,
            'unmatched': len(source_meta['objects']) - matched}


def explain_diff(diff: dict[str, Any]) -> list[str]:
    """Человекочитаемые причины расхождений структур из diff_structures.

    diff — результат diff_structures ({only_source, only_target,
    type_mismatch, counts}).
    """
    out: list[str] = []
    for key in diff.get('only_source') or []:
        out.append(f'Только в источнике: объект/поле {key} отсутствует в приёмнике.')
    for key in diff.get('only_target') or []:
        out.append(f'Только в приёмнике: {key} нет в источнике.')
    for item in diff.get('type_mismatch') or []:
        out.append(f'Изменён тип: {item.get("object")}.{item.get("attr")} '
                   f'{item.get("source_type")} -> {item.get("target_type")}.')
    if not out:
        out.append('Структуры совпадают.')
    return out


def compress_metadata(meta: dict[str, Any],
                      top_tables: int = 15,
                      out_path: str | Path | None = None) -> dict[str, Any]:
    """Сжать метаданные (тысячи объектов) до краткого саммари для LLM.

    Возвращает {kinds:{kind: count}, objects, tables, top:[...], total}.
    top — первые по числу реквизитов (грубая оценка объёма).
    out_path — опционально сохранить саммари JSON-файлом для переиспользования
    между вызовами агента без пересчёта.
    """
    objs = meta.get('objects') or []
    counts: dict[str, int] = {}
    for o in objs:
        k = o.get('kind') or '?'
        counts[k] = counts.get(k, 0) + 1
    ranked = sorted(objs, key=lambda o: len(o.get('attributes') or []),
                    reverse=True)
    top = [{'kind': o.get('kind'), 'name': o.get('name'),
            'table': o.get('table'), 'attrs': len(o.get('attributes') or [])}
           for o in ranked[:top_tables]]
    summary = {'kinds': counts, 'objects': len(objs), 'tables': len(objs),
               'top': top, 'total_attrs': sum(
                   len(o.get('attributes') or []) for o in objs)}
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                     encoding='utf-8')
    return summary
