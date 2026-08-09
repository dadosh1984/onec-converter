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

import base64
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import datetime
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
    Path(path).write_text(json.dumps(objects, ensure_ascii=False, indent=1,
                                      default=_json_default), encoding='utf-8')


def load_json_batch(path: str | Path) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(Path(path).read_text(encoding='utf-8'))
    return data


def _json_default(o: Any) -> Any:
    """Сериализация нестандартных типов 1С: bytes (BLOB/хранение) -> base64."""
    if isinstance(o, bytes):
        return base64.b64encode(o).decode('ascii')
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f'Object of type {type(o).__name__} is not JSON serializable')


def save_json_stream(objects: Iterable[dict[str, Any]], path: str | Path,
                     batch_size: int = 10000) -> None:
    """Потоковая запись промежуточного JSON (по одному объекту на строку).

    Не накапливает все объекты в памяти — подходит для больших баз без OOM.
    Формат: '[{{...}},\n{{...}}]' — валидный JSON-массив (совместим с
    load_json_batch). bytes-поля кодируются в base64 (_json_default).
    """
    p = Path(path)
    with p.open('w', encoding='utf-8') as f:
        f.write('[')
        first = True
        for obj in objects:
            if not first:
                f.write(',\n')
            f.write(json.dumps(obj, ensure_ascii=False, default=_json_default))
            first = False
        f.write(']')


def load_json_stream(path: str | Path) -> Iterable[dict[str, Any]]:
    """Потоковое чтение JSON-массива: генератор объектов (без OOM).

    Формат '[\n{...},\n{...}]' — по одному объекту на строку (NDJSON).
    Учитывается, что '[' может идти на одной строке с первым объектом,
    а ']' — на одной с последним.
    """
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s.startswith('['):
                s = s[1:].lstrip()
            if s in ('[', ']', '[,', '[]'):
                continue
            s = s.removesuffix(',').rstrip()
            if s.endswith(']'):
                s = s[:-1].rstrip()
            s = s.removesuffix(',').rstrip()
            if not s:
                continue
            yield json.loads(s)
