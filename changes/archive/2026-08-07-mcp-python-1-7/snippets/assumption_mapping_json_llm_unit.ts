// GREEN: mapping — JSON-схема правил + LLM-промпт по метаданным обеих сторон
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_mapping_json_llm_unit() {
  const files: Record<string, string> = {
    'src/onec_converter/mapping.py': `"""Правила маппинга: JSON-схема + генерация промпта для LLM.

Схема правил:
    {"version": 1,
     "source_ib": "<идентификатор источника>",
     "target_ib": "<идентификатор приёмника>",
     "objects": [
        {"source": "Справочник.Номенклатура", "target": "Справочник.Номенклатура",
         "key": ["Код"],                        # естественный ключ (для ссылок)
         "attributes": {"Наименование": "Наименование", "Код": "Код"}}  # source->target
     ],
     "enums": {"Статус": "СтатусЗаказа"}}
LLM получает метаданные источника и приёмника и возвращает rules по этой схеме.
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = 1

RULES_DEFAULT: dict[str, Any] = {'version': SCHEMA_VERSION, 'objects': [], 'enums': {}}


def build_prompt(meta_source: dict[str, Any], meta_target: dict[str, Any]) -> str:
    """Промпт для LLM: сгенерировать rules по метаданным обеих сторон."""
    return (
        'Ты — эксперт по переносу данных между ИБ 1С. Составь правила сопоставления '
        'объектов и реквизитов источника и приёмника.\\n'
        'МЕТАДАННЫЕ ИСТОЧНИКА:\\n' + json.dumps(meta_source, ensure_ascii=False, indent=1) +
        '\\nМЕТАДАННЫЕ ПРИЁМНИКА:\\n' + json.dumps(meta_target, ensure_ascii=False, indent=1) +
        '\\nВерни строго JSON по схеме: ' + json.dumps(RULES_DEFAULT, ensure_ascii=False) +
        '\\nДля каждого объекта укажи: source, target, key (список реквизитов естественного ключа), '
        'attributes (source->target). Перечисления — в enums.'
    )


def validate_rules(rules: dict[str, Any]) -> list[str]:
    """Проверка правил; возвращает список ошибок (пусто — правила валидны)."""
    errors: list[str] = []
    if rules.get('version') != SCHEMA_VERSION:
        errors.append(f'неверная версия схемы: {rules.get("version")}')
    if not isinstance(rules.get('objects'), list):
        errors.append('нет поля objects')
        return errors
    seen: set[tuple[str, str]] = set()
    for i, rule in enumerate(rules['objects']):
        src = rule.get('source')
        tgt = rule.get('target')
        if not src or not tgt:
            errors.append(f'object[{i}]: требуются source и target')
            continue
        pair = (src, tgt)
        if pair in seen:
            errors.append(f'object[{i}]: дубликат пары {src}->{tgt}')
        seen.add(pair)
        if not isinstance(rule.get('attributes'), dict):
            errors.append(f'object[{i}]: attributes должен быть объектом')
    return errors
`,
    'tests/test_mapping_rules.py': `"""Unit-тесты схемы правил маппинга."""
from onec_converter.mapping import validate_rules, build_prompt, RULES_DEFAULT

import json


def test_valid_rules():
    rules = {'version': 1,
             'objects': [{'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
                          'key': ['Код'], 'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}],
             'enums': {}}
    assert validate_rules(rules) == []


def test_missing_fields_reported():
    rules = {'version': 1, 'objects': [{'source': 'X', 'target': 'Y'}]}
    errors = validate_rules(rules)
    assert any('attributes' in e for e in errors)


def test_duplicate_pair_reported():
    rules = {'version': 1, 'objects': [
        {'source': 'X', 'target': 'Y', 'attributes': {}},
        {'source': 'X', 'target': 'Y', 'attributes': {}}]}
    assert any('дубликат' in e for e in validate_rules(rules))


def test_build_prompt_mentions_both_sides():
    p = build_prompt({'obj': 1}, {'obj': 2})
    assert 'ИСТОЧНИКА' in p and 'ПРИЁМНИКА' in p
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
