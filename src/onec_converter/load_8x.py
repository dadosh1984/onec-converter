"""Прямая загрузка в 1CD без HTTP-расширения (Фаза 13, zero-setup A).

После transform объект приёмника: {'type': 'Справочник.X', 'key': [...],
'attributes': {имя_реквизита: значение}} (русские имена реквизитов, как в
read_metadata). load_direct пишет объекты в КОПИЮ 1Cv8.1CD приёмника через
write_8x.append_records; оригинал никогда не изменяется.

Ограничения MVP (зафиксированы в docs/zero-setup.md):
- _IDRREF: префикс (4 байта) из первой непустой строки таблицы (или нули)
  + уникальные 12 байт; точная семантика префикса 1С не гарантируется
  (наш парсер читает без потерь);
- индексы таблиц не пересобираются (см. Фаза 12).
"""

from __future__ import annotations

import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fake_1cd import enc_datetime, enc_nc, enc_numeric, enc_nvc
from .load_8x_refs import ReceiverReferenceIndex, make_vt_row
from .source_8x_file import Database1CD, TableDef, read_metadata
from .write_8x import append_records, copy_1cd

_IDREF_LEN = 16
_PREFIX_LEN = 4


class LoadError(Exception):
    """Ошибка прямой загрузки в 1CD."""


def _encode_field(row: bytearray, fd: Any, value: Any) -> None:
    """Кодирование значения в поле строки по типу FieldDef."""
    raw: bytes | None = None
    if fd.type == 'NVC':
        raw = enc_nvc(str(value), fd.length, fd.null_exists)
    elif fd.type == 'NC':
        raw = enc_nc(str(value), fd.length)
    elif fd.type == 'N':
        raw = enc_numeric(float(value), fd.length, fd.precision)
    elif fd.type == 'L':
        raw = b'\x01' if value else b'\x00'
    elif fd.type == 'DT':
        raw = enc_datetime(str(value))
    elif fd.type in ('B', 'RV') and isinstance(value, bytes) and len(value) == 16:
        raw = value
    if raw is None:
        return
    row[fd.offset:fd.offset + len(raw)] = raw


@dataclass(frozen=True)
class FieldMap:
    """Русское имя реквизита -> физическое поле таблицы."""

    name: str
    field: str
    ftype: str
    length: int
    precision: int


def object_to_row(table: TableDef, fields: list[FieldMap], obj: dict[str, Any],
                  idref: bytes, ref_index: Any | None = None,
                  references: dict[str, Any] | None = None) -> bytes:
    """Строка таблицы 1CD из объекта приёмника (после transform).

    _VERSION/_MARKED и прочие служебные поля — нули; _IDRREF — idref;
    _CODE/_DESCRIPTION — из key или атрибутов «Код»/«Наименование»;
    _NUMBER/_DATE_TIME/_POSTED — из атрибутов документа (Фаза 15);
    REF-поля — резолв через ref_index (Фаза 15);
    остальные атрибуты — по полям таблицы (русские имена).
    """
    row = bytearray(table.row_length or 1)
    attrs = obj.get('attributes') or {}
    key = obj.get('key') or []
    refs = references if references is not None else (obj.get('references') or {})
    by_field = {fm.field: fm for fm in fields}
    for fd in table.fields.values():
        if fd.name == '_IDRREF' and len(idref) == _IDREF_LEN:
            row[fd.offset:fd.offset + _IDREF_LEN] = idref
            continue
        if fd.name in ('_VERSION', '_MARKED', '_ISMETADATA', '_FOLDER',
                       '_ORDERFIELD'):
            continue  # нули
        fm = by_field.get(fd.name)
        # REF-поле (B16) — резолв из references по имени реквизита
        if fm is not None and fm.ftype == 'ref':
            if fm.name in refs:
                raw_ref = _resolve_ref(refs[fm.name], ref_index)
                row[fd.offset:fd.offset + 16] = raw_ref
            continue
        value: Any = None
        if fm is not None:
            value = attrs.get(fm.name)
        elif fd.name == '_CODE':
            value = attrs.get('Код', key[0] if key else None)
        elif fd.name == '_DESCRIPTION':
            value = attrs.get('Наименование',
                              key[1] if len(key) > 1 else None)
        elif fd.name == '_NUMBER':
            value = attrs.get('Номер', key[0] if key else None)
        elif fd.name == '_DATE_TIME':
            value = attrs.get('Дата')
        elif fd.name == '_POSTED':
            value = attrs.get('Проведён')
        if value is not None:
            _encode_field(row, fd, value)
    return bytes(row)


def _resolve_ref(ref_value: Any, ref_index: Any) -> bytes:
    """16 байт _IDRREF приёмника из значения 'Тип:ключ1|ключ2'.

    ref_index — {obj_type: (таблица, ReceiverReferenceIndex)} либо объект
    с методом resolve(table, key). Не резолвится/не найден — 16 нулей.
    """
    zero = b'\x00' * _IDREF_LEN
    if not isinstance(ref_value, str) or ':' not in ref_value:
        # уже готовая ссылка (bytes) или ссылка без типа — берём как есть
        if isinstance(ref_value, bytes) and len(ref_value) == _IDREF_LEN:
            return ref_value
        return zero
    obj_type, key_part = ref_value.split(':', 1)
    key = tuple(key_part.split('|'))
    if ref_index is None:
        return zero
    entry = ref_index.get(obj_type)
    if entry is None:
        return zero
    table_name, index = entry
    raw = index.resolve(table_name, key)
    return raw if raw is not None else zero


def _idref_prefix(db: Database1CD, table_name: str) -> bytes:
    """Первые 4 байта из первой непустой строки таблицы (или нули)."""
    t = db.tables[table_name]
    idr = t.fields.get('_IDRREF')
    if idr is None:
        return b'\x00' * _PREFIX_LEN
    for row in db.table_rows(t):
        if row[:1] == b'\x01':
            continue
        raw = row[idr.offset:idr.offset + _IDREF_LEN]
        if raw != b'\x00' * _IDREF_LEN:
            return raw[:_PREFIX_LEN]
    return b'\x00' * _PREFIX_LEN


def _table_for(obj_type: str, index: dict[str, dict[str, Any]],
               tables: dict[str, TableDef]) -> tuple[dict[str, Any], TableDef]:
    """(объект конфигурации, таблица) по типу 'Справочник.X' из intermediate."""
    meta = index.get(obj_type)
    if meta is None:
        raise LoadError(f'нет объекта приёмника {obj_type!r} в метаданных')
    table = tables.get(meta.get('table', ''))
    if table is None:
        raise LoadError(f'нет таблицы {meta.get("table")!r} для {obj_type!r}')
    return meta, table


def _field_map(meta: dict[str, Any]) -> list[FieldMap]:
    out: list[FieldMap] = []
    for a in meta.get('attributes') or []:
        out.append(FieldMap(a['name'], a['field'], a['type'],
                            a.get('length', 0), a.get('precision', 0)))
    return out


def load_direct(target_dir: str | Path, objects: list[dict[str, Any]],
                workdir: str | Path | None = None) -> dict[str, Any]:
    """Прямая запись объектов в КОПИЮ приёмника; оригинал не изменяется.

    Возвращает {'ok', 'copy_path', 'total', 'tables': {таблица: n},
    'ref_warnings': [...]}. Документы и табличные части (Фаза 15): REF-поля
    резолвятся в _IDRREF приёмника, ненайденные — 16 нулей + ref_warnings.
    """
    target = Path(target_dir)
    cd = target / '1Cv8.1CD'
    if not cd.is_file():
        raise LoadError(f'нет 1Cv8.1CD в {target_dir}')
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix='onec_load_'))
    wd.mkdir(parents=True, exist_ok=True)
    cp = copy_1cd(cd, wd / '1Cv8.1CD')

    md = read_metadata(cp)
    # meta index: 'Справочник.X' -> {table, ...}
    index = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}
    rows_by_table: dict[str, list[bytes]] = {}
    prefix_by_table: dict[str, bytes] = {}
    idref_counter: dict[str, int] = {}
    ref_warnings: list[str] = []
    vt_rows_by_table: dict[str, list[bytes]] = {}
    # собрать типы, на которые ссылаются объекты (для построения индексов)
    ref_types: set[str] = set()
    for obj in objects:
        t = obj.get('type')
        if t:
            ref_types.add(t)
        for val in (obj.get('references') or {}).values():
            if isinstance(val, str) and ':' in val:
                ref_types.add(val.split(':', 1)[0])
    with Database1CD(cp) as db:
        # obj_type -> (таблица приёмника, ReceiverReferenceIndex)
        ref_index: dict[str, Any] = {}
        for rt in sorted(ref_types):
            rmeta = index.get(rt)
            if not rmeta:
                continue
            rtab = rmeta.get('table')
            if rtab and rtab in db.tables:
                ref_index[rt] = (rtab, _build_receiver_index(db, rtab))
        for obj in objects:
            obj_type = obj.get('type')
            if not obj_type:
                raise LoadError(f'объект без type: {obj}')
            meta, table = _table_for(obj_type, index, db.tables)
            fm = _field_map(meta)
            table_name = meta['table']
            if table_name not in prefix_by_table:
                prefix_by_table[table_name] = _idref_prefix(db, table_name)
                idref_counter[table_name] = 0
            n = idref_counter[table_name]
            idref_counter[table_name] += 1
            idref = _make_idref(prefix_by_table[table_name], n)
            references = obj.get('references') or {}
            row = object_to_row(table, fm, obj, idref,
                                ref_index=ref_index, references=references)
            rows_by_table.setdefault(table_name, []).append(row)
            _ref_report(obj_type, references, ref_index, meta, ref_warnings)
            # табличные части (Фаза 15)
            for ts in (obj.get('tab_sections') or {}).values():
                vt_table = _vt_table_for(db, table_name)
                if vt_table is None:
                    continue
                for i, r in enumerate(ts.get('rows') or []):
                    vrow = make_vt_row(vt_table, idref, i + 1, r)
                    vt_rows_by_table.setdefault(vt_table.name, []).append(vrow)

    tables_stat: dict[str, int] = {}
    for table_name, rows in rows_by_table.items():
        n = append_records(cp, table_name, b''.join(rows))
        tables_stat[table_name] = n
    for table_name, rows in vt_rows_by_table.items():
        n = append_records(cp, table_name, b''.join(rows))
        tables_stat[table_name] = n
    return {'ok': True, 'copy_path': str(cp), 'total': len(objects),
            'tables': tables_stat, 'ref_warnings': ref_warnings}


def _build_receiver_index(db: Database1CD, table_name: str
                          ) -> ReceiverReferenceIndex:
    ind = ReceiverReferenceIndex()
    ind.build_table(db, table_name)
    return ind


def _vt_table_for(db: Database1CD, base_table: str
                  ) -> Any | None:
    """Первая _VT-таблица заданной базовой таблицы (по префиксу имени)."""
    prefix = base_table + '_VT'
    for name in db.tables:
        if name.startswith(prefix):
            return db.tables[name]
    return None


def _ref_report(obj_type: str, references: dict[str, Any],
                ref_index: dict[str, Any], meta: dict[str, Any],
                ref_warnings: list[str]) -> None:
    """Проверить резолв каждого REF-реквизита и пополнить ref_warnings."""
    for ref_name, val in references.items():
        if not isinstance(val, str) or ':' not in val:
            continue
        ot, keyp = val.split(':', 1)
        key = tuple(keyp.split('|'))
        entry = ref_index.get(ot)
        if entry is None:
            ref_warnings.append(f'{obj_type}:{ref_name}: нет индекса для {ot}')
            continue
        tbl, ind = entry
        if ind.resolve(tbl, key) is None:
            ref_warnings.append(f'{obj_type}:{ref_name}: ненайден ref {ot}:{keyp}')


def _make_idref(prefix: bytes, counter: int) -> bytes:
    """16 байт: префикс (4) + счётчик (8) + нули (4)."""
    return prefix + struct.pack('<Q', counter) + b'\x00' * 4
