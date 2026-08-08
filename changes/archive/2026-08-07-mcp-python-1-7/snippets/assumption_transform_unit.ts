// GREEN: transform — применение правил к данным (типы, перечисления, ссылки)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_transform_unit() {
  const files: Record<string, string> = {
    'src/onec_converter/transform.py': `"""Применение правил маппинга к данным источника.

Вход: объект источника (intermediate-представление) + правила объекта (mapping).
Выход: целевой объект (словарь атрибутов в терминах приёмника), пригодный для load.
Ссылки разрешаются через RefResolver; перечисления — по таблице enums.
"""

from __future__ import annotations

from typing import Any

from .intermediate import OBJ_TYPE, OBJ_KEY, OBJ_ATTRS, OBJ_REFS
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
`,
    'tests/test_transform.py': `"""Unit-тесты transform."""
from onec_converter.intermediate import make_object
from onec_converter.resolver import RefResolver
from onec_converter.transform import transform_object, TransformError

import pytest


def test_transform_renames_attributes():
    obj = make_object('Справочник.Банки', 'S1', ['0001', 'Банк'],
                      {'Код': '0001', 'Имя': 'Банк'}, {})
    rule = {'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
            'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}
    out = transform_object(obj, rule, RefResolver())
    assert out['attributes'] == {'Код': '0001', 'Наименование': 'Банк'}
    assert out['type'] == 'Справочник.Банки'


def test_transform_resolves_refs():
    targets = [make_object('Справочник.Банки', 'T1', ['0001', 'Банк'], {}, {})]
    resolver = RefResolver()
    resolver.build(targets)
    obj = make_object('Справочник.Организации', 'S2', ['OOO'],
                      {}, {'Банк': 'Справочник.Банки:0001|Банк'})
    rule = {'source': 'x', 'target': 'Справочник.Организации', 'attributes': {}}
    out = transform_object(obj, rule, resolver)
    assert out['references']['Банк'] == 'T1'


def test_transform_missing_attr_raises():
    obj = make_object('X', 'S1', ['1'], {}, {})
    rule = {'source': 'X', 'target': 'Y', 'attributes': {'Нет': 'Да'}}
    with pytest.raises(TransformError):
        transform_object(obj, rule, RefResolver())
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
