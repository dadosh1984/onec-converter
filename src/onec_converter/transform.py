"""Применение правил маппинга к данным источника.

Вход: объект источника (intermediate-представление) + правила объекта (mapping).
Выход: целевой объект (словарь атрибутов в терминах приёмника), пригодный для load.
Ссылки разрешаются через RefResolver; перечисления — по таблице enums.
"""

from __future__ import annotations

from typing import Any

from .intermediate import OBJ_ATTRS, OBJ_KEY, OBJ_REFS, OBJ_TYPE
from .resolver import RefResolver


class TransformError(Exception):
    """Ошибка трансформации объекта."""


def transform_object(
    obj: dict[str, Any],
    rule: dict[str, Any],
    resolver: RefResolver,
    enums: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Преобразовать объект источника в целевой формат по правилу."""
    enums = enums or {}
    attrs: dict[str, Any] = {}
    src_attrs = obj[OBJ_ATTRS]
    for src_name, tgt_name in (rule.get('attributes') or {}).items():
        if src_name not in src_attrs:
            raise TransformError(f'нет реквизита {src_name} в объекте {obj.get("type")}')
        value = src_attrs[src_name]
        if value is not None and src_name in enums:
            mapped = enums[src_name]
            # значение перечисления переносится как имя целевого значения
            value = mapped if isinstance(mapped, str) else mapped.get(str(value), value)
        attrs[tgt_name] = value

    refs: dict[str, Any] = {}
    for ref_name, target_ref in (obj[OBJ_REFS] or {}).items():
        # target_ref: "Справочник.X:ключ1|ключ2"
        if ':' not in target_ref:
            refs[ref_name] = target_ref
            continue
        obj_type, key_part = target_ref.split(':', 1)
        key = tuple(key_part.split('|'))
        resolved = resolver.resolve(obj_type, key, obj[OBJ_KEY][0])
        refs[ref_name] = resolved

    return {
        'type': rule.get('target', obj[OBJ_TYPE]),
        'key': obj[OBJ_KEY],
        'attributes': attrs,
        'references': refs,
    }
