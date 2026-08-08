"""Импорт правил обмена «Конвертации данных 3» (XML) в JSON-правила TOON — идея B3.

Источник идеи: otymko/gitrules — разбор XML правил конвертации/регистрации
на файлы/каталоги. Здесь — импорт упрощённого XML правил обмена в наш формат
(см. `mapping.load_rules/save_rules`), чтобы готовые правила экосистемы 1С
были переносимы в пайплайн onec-converter.

Импортируемая структура (документированный подмножество КД3-правил):

    <?xml version="1.0" encoding="UTF-8"?>
    <ConversionRules version="1">
      <Mapping source="Справочник.Номенклатура" target="Справочник.Номенклатура">
        <Key>Код</Key>
        <Attribute source="Наименование" target="Наименование"/>
        <Attribute source="Код" target="Код"/>
      </Mapping>
      <Enum source="Статус" target="СтатусЗаказа"/>
    </ConversionRules>

`source`/`target` — полные имена объектов («Тип.Имя»); `<Key>` — естественный
ключ; `<Attribute>` — пара реквизитов. Ошибки XML/схемы -> Kd3ImportError.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .mapping import SCHEMA_VERSION


class Kd3ImportError(Exception):
    """Ошибка импорта правил обмена."""


def import_kd3_xml(path: str | Path) -> dict[str, Any]:
    """XML правил обмена -> правила TOON (наш JSON-формат маппинга)."""
    p = Path(path)
    try:
        root = ET.parse(p).getroot()
    except (OSError, ET.ParseError) as exc:
        raise Kd3ImportError(f'не удалось разобрать XML {p}: {exc}') from exc

    objects: list[dict[str, Any]] = []
    enums: dict[str, str] = {}

    for mapping in root.findall('Mapping'):
        src = mapping.get('source')
        tgt = mapping.get('target')
        if not src or not tgt:
            raise Kd3ImportError(f'Mapping без source/target в {p}')
        rule: dict[str, Any] = {'source': src, 'target': tgt,
                                'attributes': {}}
        key_el = mapping.find('Key')
        if key_el is not None and key_el.text and key_el.text.strip():
            rule['key'] = [key_el.text.strip()]
        for attr in mapping.findall('Attribute'):
            a_src = attr.get('source')
            a_tgt = attr.get('target')
            if not a_src or not a_tgt:
                raise Kd3ImportError(f'Attribute без source/target в {p}')
            rule['attributes'][a_src] = a_tgt
        objects.append(rule)

    for enum in root.findall('Enum'):
        e_src = enum.get('source')
        e_tgt = enum.get('target')
        if e_src and e_tgt:
            enums[e_src] = e_tgt

    return {'version': SCHEMA_VERSION, 'objects': objects, 'enums': enums}
