"""Классификация объектов ИБ: какие данные вносит пользователь (user),
какие формирует сама ИБ формулами (formula), какие служебные (service).

Правило: пользователь вносит статичные данные (справочники, документы,
константы, регистры сведений); ИБ формирует динамичные (отчёты, обработки,
движения регистров-результатов при проведении документов).
"""
from __future__ import annotations

from typing import Any

USER_KINDS = frozenset({
    'Справочник', 'Документ', 'Константа', 'РегистрСведений',
})
FORMULA_KINDS = frozenset({
    'Отчет', 'Обработка', 'РегистрНакопления', 'РегистрБухгалтерии',
    'РегистрРасчета', 'Журнал', 'ОпределяемыйТип',
})
# Всё остальное (ОбщийМодуль, ОбщаяФорма, Роль, Подсистема, ...) — service.


def classify_objects(meta: dict[str, Any]) -> dict[str, str]:
    """meta['objects']: [{kind, name}] -> {'<kind>.<name>': 'user|formula|service'}."""
    result: dict[str, str] = {}
    for obj in meta.get('objects', []):
        kind = obj.get('kind', '')
        name = obj.get('name', '')
        if not kind or not name:
            continue
        full = f'{kind}.{name}'
        if kind in USER_KINDS:
            result[full] = 'user'
        elif kind in FORMULA_KINDS:
            result[full] = 'formula'
        else:
            result[full] = 'service'
    return result



def _attr_key(a: dict[str, Any]) -> tuple[str, Any, Any]:
    """Ключ реквизита для сравнения: (имя, тип, длина)."""
    return (a.get('name', ''), a.get('type', ''), a.get('length', 0))


def compare_user_metadata(source_meta: dict[str, Any],
                          target_meta: dict[str, Any]) -> dict[str, Any]:
    """Сравнить структуру user-объектов источника и приёмника (шаги 5-6).

    Для каждого user-объекта (по classify_objects) сверяются: наличие
    объекта и его таблицы в приёмнике, состав реквизитов (имя+тип+длина),
    присутствие VT-таблиц (табличные части документов). Возвращает
    {'ok': [fullname...], 'conflict': [{'name', 'kind', 'diff': [...]}]}.
    """
    srcs = {o['kind'] + '.' + o['name']: o
            for o in source_meta.get('objects', [])}
    tgts = {o['kind'] + '.' + o['name']: o
            for o in target_meta.get('objects', [])}
    src_tables = set(source_meta.get('tables', []))
    tgt_tables = set(target_meta.get('tables', []))

    ok: list[str] = []
    conflict: list[dict[str, Any]] = []
    for full, category in classify_objects(source_meta).items():
        if category != 'user' or full.split('.', 1)[0] not in {'Справочник',
                                                               'РегистрСведений',
                                                               'Документ'}:
            continue
        obj = srcs[full]
        diff: list[str] = []
        tgt = tgts.get(full)
        if tgt is None:
            diff.append('нет объекта в приёмнике')
        else:
            base = obj.get('table', '')
            if tgt.get('table') != base:
                diff.append(f'таблица различается: {base!r} vs {tgt.get("table")!r}')
            elif base:
                if base not in tgt_tables:
                    diff.append(f'нет таблицы {base!r} в приёмнике')
                src_attrs = {_attr_key(a) for a in (obj.get('attributes') or [])}
                tgt_attrs = {_attr_key(a) for a in (tgt.get('attributes') or [])}
                only_src = {k[0] for k in src_attrs - tgt_attrs if k[2]}
                only_tgt = {k[0] for k in tgt_attrs - src_attrs if k[2]}
                if only_src:
                    diff.append(f'реквизиты только в источнике: {sorted(only_src)[:6]}')
                if only_tgt:
                    diff.append(f'реквизиты только в приёмнике: {sorted(only_tgt)[:6]}')
            # VT-таблицы документа (табличные части)
            for vt in sorted(t for t in src_tables if t.startswith(f'{base}_VT')):
                if vt not in tgt_tables:
                    diff.append(f'нет табличной части {vt!r} в приёмнике')
        if diff:
            conflict.append({'name': full, 'kind': obj.get('kind', ''),
                             'diff': diff})
        else:
            ok.append(full)
    return {'ok': sorted(ok), 'conflict': conflict}


def build_plan(meta: dict[str, Any]) -> list[dict[str, str]]:
    """План переноса: только user-объекты, каждый в отдельный файл моста.

    Справочник/РегистрСведений — как есть; Документ — шапка + по одному
    разделу на каждую табличную часть ('Документ.Х.ТЧ.<таблица>').
    Остальные user-объекты (Константа и др.) пока не переносятся.
    """
    supported = {'Справочник', 'РегистрСведений', 'Документ'}
    tables = set(meta.get('tables', []))
    plan: list[dict[str, str]] = []
    for full, category in classify_objects(meta).items():
        if category != 'user':
            continue
        kind = full.split('.', 1)[0]
        if kind not in supported:
            continue
        if kind == 'Документ':
            # шапка документа
            plan.append({'name': full, 'category': category,
                         'file': f'{full}.xlsx'})
            # табличные части: физические таблицы <таблица>_VT...
            obj = next((o for o in meta.get('objects', [])
                        if f"{o['kind']}.{o['name']}" == full), None)
            if obj:
                base = obj.get('table', '')
                for vt in sorted(t for t in tables if t.startswith(f'{base}_VT')):
                    vt_full = f'{full}.ТЧ.{vt}'
                    plan.append({'name': vt_full, 'category': category,
                                 'file': f'{vt_full}.xlsx'})
            continue
        plan.append({'name': full, 'category': category,
                     'file': f'{full}.xlsx'})
    return plan
