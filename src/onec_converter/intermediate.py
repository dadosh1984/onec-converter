"""Промежуточный формат переноса: объекты в XML/JSON.

Внутреннее представление объекта (модель источника) — словарь:
    {"type": "Справочник.Номенклатура",
     "id": "193|",
     "key": ["00001", "Шуруповёрт"],          # естественный ключ (код/наименование)
     "attributes": {"Код": "00001", "Наименование": "Шуруповёрт", ...},
     "references": {"Владелец": "Справочник.Банки:Банки РУз", ...}}  # ссылки как ключи
Сериализация: JSON (машинный), XML (ElementTree). Обратная десериализация — для load.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

OBJ_TYPE = 'type'
OBJ_ID = 'id'
OBJ_KEY = 'key'
OBJ_ATTRS = 'attributes'
OBJ_REFS = 'references'


def make_object(obj_type: str, obj_id: str, key: list[str],
                attributes: dict[str, Any], references: dict[str, str]) -> dict[str, Any]:
    return {OBJ_TYPE: obj_type, OBJ_ID: obj_id, OBJ_KEY: key,
            OBJ_ATTRS: attributes, OBJ_REFS: references}


def to_json(obj: dict[str, Any], **kwargs: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, **kwargs)


def from_json(text: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(text)
    return data


def to_xml(obj: dict[str, Any]) -> str:
    root = ET.Element('Object', {'type': obj[OBJ_TYPE], 'id': obj[OBJ_ID]})
    key_el = ET.SubElement(root, 'Key')
    for part in obj[OBJ_KEY]:
        ET.SubElement(key_el, 'Part').text = str(part)
    attrs = ET.SubElement(root, 'Attributes')
    for name, value in obj[OBJ_ATTRS].items():
        ET.SubElement(attrs, 'A', {'name': name}).text = '' if value is None else str(value)
    refs = ET.SubElement(root, 'References')
    for name, target in obj[OBJ_REFS].items():
        ET.SubElement(refs, 'R', {'name': name}).text = target
    return ET.tostring(root, encoding='unicode')


def save_json_batch(objects: list[dict[str, Any]], path: str | Path) -> None:
    Path(path).write_text(json.dumps(objects, ensure_ascii=False, indent=1), encoding='utf-8')


def load_json_batch(path: str | Path) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(Path(path).read_text(encoding='utf-8'))
    return data
