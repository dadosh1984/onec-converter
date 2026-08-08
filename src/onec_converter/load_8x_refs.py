"""REF-резолв и табличные части для load_direct (Фаза 15).

Отдельный модуль: индекс приёмника (таблица, ключ) -> _IDRREF, резолв
значения 'Тип:ключ|ключ2' в 16-байтную ссылку, сборка строк базового
документа и _VT-таблиц. Запись только на копиях (как load_8x).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .fake_1cd import enc_datetime, enc_nc, enc_numeric, enc_nvc
from .source_8x_file import Database1CD, decode_nc, decode_nvc

ZERO16 = b'\x00' * 16


@dataclass
class ReceiverReferenceIndex:
    """(имя таблицы, кортеж ключей) -> 16 байт _IDRREF приёмника."""

    _map: dict[tuple[str, tuple[str, ...]], bytes] = field(default_factory=dict)
    _built: set[str] = field(default_factory=set)

    def build_table(self, db: Database1CD, table_name: str) -> None:
        if table_name in self._built:
            return
        self._built.add(table_name)
        t = db.tables.get(table_name)
        if t is None or '_IDRREF' not in t.fields:
            return
        idr = t.fields['_IDRREF']
        code = t.fields.get('_CODE')
        descr = t.fields.get('_DESCRIPTION')
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            raw = row[idr.offset:idr.offset + 16]
            if raw == ZERO16:
                continue
            key: list[str] = []
            if code is not None:
                key.append(decode_nc(row[code.offset:code.offset + code.size]))
            if descr is not None:
                key.append(_nvc_text(row, descr))
            self._map[(table_name, tuple(key))] = raw

    def resolve(self, table_name: str, key: tuple[str, ...]) -> bytes | None:
        return self._map.get((table_name, key))


def _nvc_text(row: bytes, fd: Any) -> str:
    try:
        return decode_nvc(row[fd.offset:fd.offset + fd.size], fd.null_exists) or ''
    except (IndexError, UnicodeDecodeError):
        return ''


def _enc(row: bytearray, fd: Any, value: Any) -> None:
    """Закодировать значение в поле по типу FieldDef (как object_to_row)."""
    raw: bytes | None = None
    ft = fd.type
    if ft == 'NVC':
        raw = enc_nvc(str(value), fd.length, fd.null_exists)
    elif ft == 'NC':
        raw = enc_nc(str(value), fd.length)
    elif ft == 'N':
        raw = enc_numeric(float(value), fd.length, fd.precision)
    elif ft == 'L':
        raw = b'\x01' if value else b'\x00'
    elif ft == 'DT':
        raw = enc_datetime(str(value))
    elif ft in ('B', 'RV') and isinstance(value, bytes) and len(value) == 16:
        raw = value
    if raw is not None:
        row[fd.offset:fd.offset + len(raw)] = raw


def make_vt_row(vt_table: Any, parent_idref: bytes, line: int,
                attrs: dict[str, Any]) -> bytes:
    """Строка _VT: parent '_<Base>IDRREF'(16б) + _KEYFIELD(0) + LINENO + реквизиты.

    attrs — {физическое_имя_поля: значение}; RECord реквизиты строки (NVC/NC/N/
    L/DT/REF-B16) кодируются, служебные пропускаются.
    """
    row = bytearray(vt_table.row_length or 1)
    parent_field = next((f for f in vt_table.fields.values()
                         if f.name.endswith('IDRREF')
                         and len(f.name) > len('_IDRREF')), None)
    if parent_field is not None:
        row[parent_field.offset:parent_field.offset + 16] = parent_idref
    keyf = vt_table.fields.get('_KEYFIELD')
    if keyf is not None:
        row[keyf.offset] = 0
    line_field = next((f for f in vt_table.fields.values()
                       if f.name.upper().startswith('_LINENO')), None)
    if line_field is not None:
        raw = enc_numeric(float(line), line_field.length, 0)
        row[line_field.offset:line_field.offset + min(len(raw), line_field.size)] = raw
    for fname, fd in vt_table.fields.items():
        if fname in attrs:
            _enc(row, fd, attrs[fname])
    return bytes(row)
