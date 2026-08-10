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


def build_plan(meta: dict[str, Any]) -> list[dict[str, str]]:
    """План переноса: только user-объекты, каждый в отдельный файл моста.

    Экспорт моста (export_bridge) умеет Справочник и РегистрСведений;
    остальные user-объекты (Документ и др.) — не переносятся, пока
    выгрузка моста для них не реализована.
    """
    supported = {'Справочник', 'РегистрСведений'}
    plan: list[dict[str, str]] = []
    for full, category in classify_objects(meta).items():
        if category != 'user':
            continue
        kind = full.split('.', 1)[0]
        if kind not in supported:
            continue
        plan.append({'name': full, 'category': category,
                     'file': f'{full}.xlsx'})
    return plan
