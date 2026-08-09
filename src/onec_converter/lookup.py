"""Резолвер ссылок по полю поиска (аналог ПолучитьВозможныеЗначения .epf).

Индекс приёмника: (тип объекта, поле поиска, значение) -> список _IDRREF.
Поля поиска: 'Код' (_CODE), 'Наименование' (_DESCRIPTION), 'Номер' (_NUMBER),
'Дата' (_DATE_TIME) или реквизит по русскому имени (через field_map).
Значения нормализуются в строку (числа/даты — как в типизаторе).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .source_8x_file import Database1CD, decode_field

ZERO16 = b'\x00' * 16

# служебное поле -> русское имя (как в intermediate/load_8x)
_SERVICE = {'_CODE': 'Код', '_DESCRIPTION': 'Наименование', '_NUMBER': 'Номер',
            '_DATE_TIME': 'Дата'}


@dataclass
class FieldLookupIndex:
    """(obj_type, поле, значение) -> список _IDRREF приёмника."""

    _map: dict[tuple[str, str, str], list[bytes]] = field(default_factory=dict)
    _byday: dict[tuple[str, str, str], list[bytes]] = field(default_factory=dict)
    _owners: dict[tuple[str, str, str], list[bytes | None]] = field(default_factory=dict)
    _built: set[tuple[str, str]] = field(default_factory=set)
    _built_day: set[tuple[str, str]] = field(default_factory=set)

    def build_field(self, db: Database1CD, obj_type: str, table_name: str,
                    field_map: dict[str, str], field_name: str) -> None:
        """Построить индекс по одному полю поиска (идемпотентно).

        field_map — русское имя реквизита -> физическое поле (см. _field_map
        в load_8x); для 'Код'/'Наименование'/'Номер'/'Дата' маппинг служебный.
        Для подчинённых/иерархических справочников дополнительно запоминается
        владелец записи (_OWNERIDRREF) — фильтруется через resolve(owner=...).
        """
        key = (obj_type, field_name)
        if key in self._built:
            return
        self._built.add(key)
        t = db.tables.get(table_name)
        if t is None:
            return
        idr = t.fields.get('_IDRREF')
        if idr is None:
            return
        fld = _physical(t, field_map, field_name)
        if fld is None:
            return
        owner_f = t.fields.get('_OWNERIDRREF')
        for row in db.table_rows(t):
            if row[:1] == b'\x01' or len(row) < 16:
                continue
            raw_id = row[idr.offset:idr.offset + 16]
            if raw_id == ZERO16:
                continue
            value = _decode(fld, row)
            if value in (None, ''):
                continue
            key_v = _norm(value)
            owner = None
            if owner_f is not None:
                o = row[owner_f.offset:owner_f.offset + 16]
                owner = None if o == ZERO16 else o
            self._map.setdefault((obj_type, field_name, key_v), []).append(raw_id)
            self._owners.setdefault((obj_type, field_name, key_v), []).append(owner)
            day = _day_key(value)
            if day:
                self._byday.setdefault((obj_type, field_name, day), []).append(raw_id)

    def resolve(self, obj_type: str, field_name: str, value: Any,
                owner: bytes | None = None) -> list[bytes]:
        """Список _IDRREF приёмника по значению поля поиска.

        owner — необязательный фильтр по владельцу (подчинённые справочники):
        вернуть только записи, принадлежащие этому владельцу (16 байт ссылки).
        """
        ids = list(self._map.get((obj_type, field_name, _norm(value)), []))
        if owner is None:
            return ids
        own = self._owners.get((obj_type, field_name, _norm(value)), [])
        return [i for i, o in zip(ids, own) if o is not None and o == owner]

    def resolve_day(self, obj_type: str, field_name: str, value: Any) -> list[bytes]:
        """Список _IDRREF по календарному ДНЮ значения (для полей «Дата»).

        Документ «Номер от Дата»: дата в мосте может быть днём без времени,
        а в приёмнике _DATE_TIME хранит точное время — ищем по дню.
        """
        day = _day_key(value)
        if not day:
            return self.resolve(obj_type, field_name, value)
        return list(self._byday.get((obj_type, field_name, day), []))


def _physical(t: Any, field_map: dict[str, str], field_name: str) -> Any | None:
    if field_name in ('Код', 'Наименование', 'Номер', 'Дата'):
        for service, ru in _SERVICE.items():
            if ru == field_name and service in t.fields:
                return t.fields[service]
        return None
    physical = field_map.get(field_name)
    if physical and physical in t.fields:
        return t.fields[physical]
    return None


def _decode(fld: Any, row: bytes) -> Any:
    try:
        return decode_field(fld, row[fld.offset:fld.offset + fld.size])
    except (IndexError, ValueError, UnicodeDecodeError):
        return None


def _norm(value: Any) -> str:
    """Нормализация значения в строку индекса (как типизатор)."""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _day_key(value: Any) -> str:
    """'YYYY-MM-DD' для datetime/date/datetime.text-строки, иначе ''."""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    try:
        if isinstance(value, str) and len(value.strip()) >= 10:
            import datetime as _d
            parsed = _d.datetime.strptime(value.strip()[:19], '%Y-%m-%d %H:%M:%S')
            return parsed.strftime('%Y-%m-%d')
    except ValueError:
        pass
    return ''
