"""Экспорт правил TOON в XML в стиле КД3 (2).

XML-представление правил маппинга (rules.json TOON) в структуре,
близкой к «Конвертации данных 3»: DataContainer → Rules → Rule
(source/target, атрибуты). Формат авторский, упрощённый — для ревью
правил в git/контракте, НЕ бинарный формат КД3 1С.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path


class Kd3Error(Exception):
    """Ошибка экспорта правил в КД3-XML."""


def export_kd3(rules_path: str | Path, out_file: str = '') -> dict[str, object]:
    """Конвертация rules.json (TOON) в XML КД3-стиля.

    Структура: <DataContainer><Rules><Rule source target>
      <Attributes><Attribute source target/></Attributes></Rule>...
    enums — как <EnumMappings><Mapping source target/>.
    Возвращает {ok, rules, enums, xml}; out_file — запись файла.
    """
    p = Path(rules_path)
    if not p.is_file():
        raise Kd3Error(f'нет файла правил: {rules_path}')
    try:
        rules = json.loads(p.read_text(encoding='utf-8'))
    except ValueError as exc:
        raise Kd3Error(f'правила не JSON: {exc}') from exc
    if rules.get('version') != 1 or not isinstance(rules.get('objects'), list):
        raise Kd3Error('неверная схема правил (ожидается TOON version=1)')

    root = ET.Element('DataContainer')
    rules_el = ET.SubElement(root, 'Rules')
    for r in rules['objects']:
        rule = ET.SubElement(rules_el, 'Rule',
                             {'source': str(r.get('source', '')),
                              'target': str(r.get('target', ''))})
        attrs = ET.SubElement(rule, 'Attributes')
        for src, tgt in (r.get('attributes') or {}).items():
            ET.SubElement(attrs, 'Attribute',
                          {'source': src, 'target': str(tgt)})
    enums = rules.get('enums') or {}
    if enums:
        em = ET.SubElement(root, 'EnumMappings')
        for src, tgt in enums.items():
            ET.SubElement(em, 'Mapping',
                          {'source': src, 'target': str(tgt)})
    ET.indent(root)
    xml_str = ET.tostring(root, encoding='unicode', xml_declaration=True)
    if out_file:
        Path(out_file).write_text(xml_str, encoding='utf-8')
    return {'ok': True, 'rules': len(rules['objects']),
            'enums': len(enums), 'xml': xml_str}
