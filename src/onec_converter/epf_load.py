"""Импорт xlsx-моста в КОПИЮ ИБ 1С 8.x — аналог .epf «ЗагрузкаДанныхИзТабличногоДокумента».

Режимы загрузки (R2C1 моста):
  0 — справочник: find-or-create по колонкам с ПолеПоиска (AND), у найденного
      объекта обновляются только отмеченные колонки (перезапись строки);
  2 — регистр сведений: запись ищется по измерениям (колонки с ПолеПоиска),
      найденная перезаписывается, отсутствующая добавляется;
  1 — табличная часть: зарезервировано, не реализовано (BridgeError).

Запись — только в копию приёмника (work-файл в workdir), оригинал не
изменяется; по завершении копия остаётся в workdir/1Cv8.1CD (как load_direct).
"""
from __future__ import annotations

import struct
import tempfile
from datetime import UTC
from datetime import datetime as _dt
from pathlib import Path
from typing import Any

from .bridge_format import (
    MODE_CATALOG,
    MODE_REGISTER,
    MODE_TABLE,
    BridgeConfig,
    ColumnSpec,
    read_bridge,
)
from .enum_resolver import EnumResolver
from .hooks import before_write, run_hook
from .load_8x_refs import _encode_field, make_vt_row
from .lookup import FieldLookupIndex, _norm
from .source_8x_file import Database1CD, decode_field, read_metadata
from .typify import KIND_DATE, KIND_REF, TypeSpec, to_value
from .write_8x import append_records, copy_1cd, overwrite_row

ZERO16 = b'\x00' * 16


class BridgeError(Exception):
    """Ошибка импорта xlsx-моста."""


def import_bridge(bridge_path: str | Path, target_dir: str | Path,
                  workdir: str | Path | None = None,
                  snapshot: bool = True,
                  max_rows: int | None = None,
                  hooks: dict[str, str] | None = None) -> dict[str, Any]:
    """Загрузить данные моста в копию приёмника; вернуть отчёт.

    {'ok', 'copy_path', 'created', 'updated', 'errors', 'snapshot'}.
    hooks: переопределение событий-хуков {'before_write', 'after_write'}.
    """
    cfg, rows = read_bridge(bridge_path)
    hk = hooks or {'before_write': cfg.before_write,
                   'after_write': cfg.after_write}
    if cfg.mode not in (MODE_CATALOG, MODE_REGISTER, MODE_TABLE):
        raise BridgeError(f'режим загрузки {cfg.mode} не реализован '
                          f'(0=справочник, 1=табличная часть, 2=регистр сведений)')
    cd = Path(target_dir) / '1Cv8.1CD'
    if not cd.is_file():
        raise BridgeError(f'нет файла приёмника: {cd}')
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix='onec_bridge_'))
    wd.mkdir(parents=True, exist_ok=True)
    snap_path: Path | None = None
    if snapshot:
        snap_path = copy_1cd(cd, wd / 'snapshot.1CD')
    work = wd / 'work.1CD'
    copy_1cd(cd, work)

    md = read_metadata(work)
    objects = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}
    obj_name, vt_name = _split_owner(cfg.obj_fullname)
    meta = objects.get(obj_name)
    if meta is None:
        raise BridgeError(f'нет объекта приёмника {cfg.obj_fullname!r} '
                          f'в метаданных')
    table_name = meta['table']
    attrs = meta.get('attributes') or []
    ru_phys = {a['name']: a['field'] for a in attrs}
    phys_ru = {a['field']: a['name'] for a in attrs}
    fm_by_name = {a['name']: a for a in attrs}
    search_cols = [c for c in cfg.columns if c.flag and c.search and c.attr]

    errors: list[dict[str, Any]] = []
    created = updated = skipped = 0
    with Database1CD(work) as db:
        if table_name not in db.tables:
            raise BridgeError(f'нет таблицы {table_name!r} в приёмнике')
        t = db.tables[table_name]
        idr = t.fields.get('_IDRREF')
        lookup = FieldLookupIndex()
        # режимы 0 (справочник) и 1 (ТЧ, по владельцу): индексы по полям поиска;
        # режим 2: позиционный индекс измерений
        if cfg.mode in (MODE_CATALOG, MODE_TABLE):
            for c in search_cols:
                lookup.build_field(db, obj_name, table_name,
                                   ru_phys, c.attr)
            prefix = _table_prefix(db, t, idr)
            counter = _max_counter(db, t, idr) if idr else 0
        else:
            reg_index = _register_index(db, t, ru_phys, search_cols)
            counter = 0
        vt_lines: dict[bytes, int] = {}  # владелец -> след. номер строки (для ТЧ)
        owner_cache: dict[tuple[str, ...], bytes] = {}
        enum_cache: dict[str, EnumResolver] = {}
        for lineno, row in enumerate(rows):
            if max_rows is not None and lineno >= max_rows:
                break
            row_no = lineno + cfg.first_data_row
            try:
                values = _row_values(cfg, row, db, objects, lookup, enum_cache)
                ctx = {'values': dict(values),
                       'texts': {c.attr: _cell_text(row, c)
                                 for c in cfg.columns if c.attr},
                       'row': row_no, 'obj_type': cfg.obj_fullname}
                proceed, values = before_write(hk['before_write'], ctx)
                if not proceed:
                    skipped += 1
                    continue
                created_here = False
                if cfg.mode == MODE_CATALOG:
                    found = _find_catalog(lookup, cfg.obj_fullname,
                                          search_cols, values)
                    if found:
                        _update_row(work, t, idr, found, values, fm_by_name,
                                    ru_phys)
                        updated += 1
                    else:
                        counter += 1
                        idref = (prefix + struct.pack('<Q', counter)
                                 + b'\x00' * 4)
                        row_bytes = _build_row(t, fm_by_name, values, idref,
                                               phys_ru)
                        append_records(work, table_name, row_bytes)
                        created += 1
                        created_here = True
                elif cfg.mode == MODE_TABLE:
                    vt = _vt_for(db, t, {}, vt_name)
                    created_owner = _load_tabular(
                        work, db, t, vt, lookup, obj_name, fm_by_name,
                        phys_ru, search_cols, cfg.columns,
                        values, vt_lines, owner_cache, cfg.no_new)
                    if created_owner:
                        created += 1
                    # строки ТЧ не меняют updated (счётчик строк см. rows_tabular)
                    created_here = bool(created_owner)
                else:  # MODE_REGISTER
                    found_idx = _find_register(reg_index, search_cols, values)
                    row_bytes = _build_row(t, fm_by_name, values, None,
                                           phys_ru)
                    if found_idx:
                        overwrite_row(work, table_name, found_idx[0], row_bytes)
                        updated += 1
                    else:
                        append_records(work, table_name, row_bytes)
                        reg_index = _register_index(db, t, ru_phys,
                                                    search_cols)
                        created += 1
                        created_here = True
                run_hook(hk['after_write'],
                         {**ctx, 'values': values, 'created': created_here})
            except Exception as exc:  # noqa: BLE001 — одна строка не рвёт загрузку
                errors.append({'row': row_no, 'error': str(exc)})
                skipped += 1

    final = wd / '1Cv8.1CD'
    work.replace(final)
    return {'ok': True, 'copy_path': str(final),
            'created': created, 'updated': updated, 'skipped': skipped,
            'errors': errors,
            'snapshot': str(snap_path) if snap_path else None}


# ---------------------------------------------------------------------------
# значения строки
# ---------------------------------------------------------------------------


def _row_values(cfg: BridgeConfig, row: list[Any],
                db: Database1CD, objects: dict[str, Any],
                lookup: FieldLookupIndex,
                enum_cache: dict[str, EnumResolver]) -> dict[str, Any]:
    """attr -> типизированное значение (только отмеченные колонки)."""
    values: dict[str, Any] = {}
    for col in cfg.columns:
        if not col.flag or not col.attr:
            continue
        if col.mode == 'Вычислять':
            ctx = {'values': dict(values), 'row': row,
                   'texts': {c.attr: _cell_text(row, c)
                             for c in cfg.columns if c.attr}}
            res = run_hook(col.lookup, ctx)
            if res is None:
                continue
            if isinstance(res, (int, float, bool, _dt)):
                v_calc = res
            else:
                v_calc, _ = to_value(col.type_spec, str(res))
            if KIND_REF in col.type_spec.kinds and isinstance(v_calc, str) and v_calc:
                v_calc = _resolve_ref(col, v_calc, db, objects, lookup, enum_cache)
            values[col.attr] = v_calc
            continue
        cell: Any = None
        if col.col_num and 0 < col.col_num <= len(row):
            cell = row[col.col_num - 1]
        if cell in (None, ''):
            v: Any = None
            if col.default:
                v = _default_value(col.default, col.type_spec)
        elif isinstance(cell, (int, float, bool, _dt)):
            v = cell  # уже типизированное значение (из экспорта)
        else:
            v, _ = to_value(col.type_spec, str(cell))
        if KIND_REF in col.type_spec.kinds and isinstance(v, str) and v:
            v = _resolve_ref(col, v, db, objects, lookup, enum_cache)
        values[col.attr] = v
    return values


def _cell_text(row: list[Any], col: ColumnSpec) -> str:
    if col.col_num and 0 < col.col_num <= len(row):
        c = row[col.col_num - 1]
        return '' if c is None else str(c)
    return ''


def _default_value(default: str, spec: TypeSpec) -> Any:
    """Базовые значения по умолчанию (аналог epf): сегодня/ТекущаяДата,
    ПустоеЗначение, НовыйОбъект, иначе — через типизатор (возврат значения).

    ТекущаяДата()/Сегодня() -> дата/время текущего момента в зависимости от
    типа колонки; ПустоеЗначение()/НовыйОбъект() -> None (поле не трогать).
    """
    d = default.strip()
    low = d.lower()
    if low in ('сегодня', 'сегодня()', 'текущаядата', 'текущаядата()',
               'текущая дата'):
        now = _dt.now(UTC)
        if KIND_DATE in spec.kinds:
            if spec.date_parts == 'time':
                return now.time()
            if spec.date_parts == 'datetime':
                return now.replace(tzinfo=None)
        return now.date()
    if low in ('пустоезначение', 'пустоезначение()', 'новыйобъект',
               'новыйобъект()'):
        return None
    v, _ = to_value(spec, default)
    return v


def _resolve_ref(col: Any, text: str, db: Database1CD,
                 objects: dict[str, Any],
                 lookup: FieldLookupIndex,
                 enum_cache: dict[str, EnumResolver]) -> bytes:
    """Текст -> 16 байт ссылки приёмника; не найдено -> 16 нулей."""
    rt = col.type_spec.ref_type or ''
    meta = objects.get(rt)
    if meta is None:
        return ZERO16
    if rt.startswith('Перечисление.'):
        resolver = enum_cache.get(rt)
        if resolver is None:
            resolver = EnumResolver(db, meta)
            enum_cache[rt] = resolver
        return resolver.by_synonym(text)
    table = meta['table']
    field_name = col.lookup or 'Наименование'
    ru_phys = {a['name']: a['field'] for a in (meta.get('attributes') or [])}
    lookup.build_field(db, rt, table, ru_phys, field_name)
    ids = lookup.resolve(rt, field_name, text)
    return ids[0] if ids else ZERO16


# ---------------------------------------------------------------------------
# поиск
# ---------------------------------------------------------------------------


def _find_catalog(lookup: FieldLookupIndex, obj_type: str,
                  search_cols: list[Any],
                  values: dict[str, Any]) -> bytes | None:
    """Первая ссылка приёмника по всем полям поиска (AND, как в epf).

    Поле «Дата» ищется по календарному дню («Номер от Дата» — дата в мосте
    может быть днём без времени). Если среди колонок поиска есть колонка,
    помеченная как СвязьПоВладельцу (owner_ref) и её значение резолвлено в
    ссылку (байты), она применяется как фильтр владельца (подчинённые
    справочники).
    """
    owner: bytes | None = None
    for c in search_cols:
        if c.owner_ref and isinstance(values.get(c.owner_ref), bytes):
            owner = values[c.owner_ref]
            break
    found: list[bytes] | None = None
    for c in search_cols:
        v = values.get(c.attr)
        if v in (None, ''):
            continue
        if c.attr == 'Дата' or _is_date_spec(c.type_spec):
            ids = lookup.resolve_day(obj_type, c.attr, v)
        else:
            ids = lookup.resolve(obj_type, c.attr, v, owner=owner)
        if not ids:
            return None
        found = ids if found is None else [i for i in found if i in ids]
        if not found:
            return None
    return found[0] if found else None


def _is_date_spec(spec: Any) -> bool:
    """Есть ли в описании типов колонки тип «дата»."""
    return KIND_DATE in getattr(spec, 'kinds', ())


def _register_index(db: Database1CD, t: Any, ru_phys: dict[str, str],
                    search_cols: list[Any]) -> dict[tuple[str, ...], list[int]]:
    """(нормализованные значения измерений) -> [позиции строк]."""
    out: dict[tuple[str, ...], list[int]] = {}
    for i, row in enumerate(db.table_rows(t)):
        if row[:1] == b'\x01':
            continue
        key = tuple(_field_value(row, t, ru_phys, c.attr)
                    for c in search_cols if c.attr)
        out.setdefault(key, []).append(i)
    return out


def _find_register(reg_index: dict[tuple[str, ...], list[int]],
                   search_cols: list[Any],
                   values: dict[str, Any]) -> list[int] | None:
    if not search_cols:
        return None  # без полей поиска — только добавление
    key = tuple(_norm(values.get(c.attr)) if values.get(c.attr) not in (None, '')
                else '' for c in search_cols if c.attr)
    return reg_index.get(key)


def _field_value(row: bytes, t: Any, ru_phys: dict[str, str],
                 attr: str) -> str:
    phys = ru_phys.get(attr)
    fd = t.fields.get(phys or '')
    if fd is None:
        return ''
    try:
        return _norm(decode_field(fd, row[fd.offset:fd.offset + fd.size]))
    except (IndexError, ValueError, UnicodeDecodeError):
        return ''


# ---------------------------------------------------------------------------
# сборка/перезапись строк
# ---------------------------------------------------------------------------


def _build_row(t: Any, fm_by_name: dict[str, Any], values: dict[str, Any],
               idref: bytes | None, phys_ru: dict[str, str]) -> bytes:
    """Строка таблицы из значений по русским именам реквизитов."""
    row = bytearray(t.row_length or 1)
    for fd in t.fields.values():
        if fd.name == '_IDRREF' and idref is not None:
            row[fd.offset:fd.offset + 16] = idref
            continue
        if fd.name in ('_VERSION', '_MARKED', '_ISMETADATA', '_FOLDER',
                       '_ORDERFIELD'):
            continue
        value: Any = None
        for attr, v in values.items():
            fm = fm_by_name.get(attr)
            if fm is not None and fm['field'] == fd.name:
                value = v
                break
        if value is not None:
            _encode_field(row, fd, value)
    return bytes(row)


def _update_row(work: Path, t: Any, idr: Any, idref: bytes,
                values: dict[str, Any], fm_by_name: dict[str, Any],
                ru_phys: dict[str, str]) -> None:
    """Прочитать строку приёмника, перезаписать отмеченные колонки, записать."""
    with Database1CD(work) as db:
        for i, row in enumerate(db.table_rows(t)):
            if row[:1] == b'\x01':
                continue
            if row[idr.offset:idr.offset + 16] == idref:
                merged = bytearray(row)
                for attr, v in values.items():
                    if v is None:
                        continue
                    fm = fm_by_name.get(attr)
                    if fm is None:
                        continue
                    fd = t.fields.get(fm['field'])
                    if fd is None:
                        continue
                    _encode_field(merged, fd, v)
                overwrite_row(work, t.name, i, bytes(merged))
                return
    raise BridgeError(f'не найдена строка {idref.hex()} для обновления')


def _split_owner(obj_fullname: str) -> tuple[str, str]:
    """'Документ.Х' -> (obj, ''); 'Документ.Х.ТЧ._VT...' -> (obj, '_VT...')."""
    parts = obj_fullname.split('.')
    if len(parts) == 4 and parts[2] == 'ТЧ':
        return '.'.join(parts[:2]), parts[3]
    return obj_fullname, ''


def _load_tabular(work: Path, db: Database1CD, t: Any, vt: Any,
                  lookup: FieldLookupIndex, obj_name: str,
                  fm_by_name: dict[str, Any],
                  phys_ru: dict[str, str], search_cols: list[ColumnSpec],
                  columns: list[ColumnSpec], values: dict[str, Any],
                  vt_lines: dict[bytes, int],
                  owner_cache: dict[tuple[str, ...], bytes], no_new: bool) -> bool:
    """Режим 1 (табличная часть): найти/создать владельца по search-колонкам,

    затем дописать строку в его VT-таблицу (реквизиты ТЧ — отмеченные не-search
    колонки). Повторные строки уже созданного в этой загрузке владельца
    находят его через owner_cache. Возвращает True, если создан новый
    объект-владелец.
    """
    own_key = tuple(_owner_key(values.get(c.attr)) for c in search_cols)
    if vt is None:
        raise BridgeError(f'у владельца {t.name!r} нет табличной части (_VT)')
    owner = _find_catalog(lookup, obj_name, search_cols, values)
    created_owner = False
    if owner is None:
        owner = owner_cache.get(own_key)
    if owner is None:
        if no_new:
            raise BridgeError('владелец не найден; НеСоздаватьНовыхЭлементов')
        idr = t.fields.get('_IDRREF')
        prefix = _table_prefix(db, t, idr)
        counter = _max_counter(db, t, idr) + 1
        owner = (prefix + struct.pack('<Q', counter) + b'\x00' * 4)
        row_bytes = _build_row(t, fm_by_name, values, owner, phys_ru)
        append_records(work, t.name, row_bytes)
        created_owner = True
        owner_cache[own_key] = owner
    line = vt_lines.get(owner, _max_line(db, vt, owner) + 1)
    vt_attrs = {c.attr: values[c.attr] for c in columns
                if c.flag and not c.search and c.attr in values}
    vrow = make_vt_row(vt, owner, line, vt_attrs)
    append_records(work, vt.name, vrow)
    vt_lines[owner] = line + 1
    return created_owner


def _owner_key(v: Any) -> str:
    """Стабильный строковый ключ значения для кеша владельцев."""
    if isinstance(v, bytes):
        return v.hex()
    return _norm(v) if v is not None else ''


def _vt_for(db: Database1CD, t: Any, vt_cache: dict[str, Any],
            vt_name: str = '') -> Any | None:
    """VT-таблица владельца: по явному имени (ТЧ из obj_fullname) или первой."""
    if vt_name:
        return db.tables.get(vt_name)
    prefix = t.name + '_VT'
    if prefix in vt_cache:
        return vt_cache[prefix]
    for name in db.tables:
        if name.startswith(prefix):
            vt_cache[prefix] = db.tables[name]
            return vt_cache[prefix]
    vt_cache[prefix] = None
    return None


def _max_line(db: Database1CD, vt: Any, owner: bytes) -> int:
    parent = next((f for f in vt.fields.values()
                   if f.name.endswith('IDRREF') and len(f.name) > 6), None)
    linef = next((f for f in vt.fields.values()
                  if f.name.upper().startswith('_LINENO')), None)
    if parent is None or linef is None:
        return 0
    m = 0
    for row in db.table_rows(vt):
        if row[:1] == b'\x01':
            continue
        if row[parent.offset:parent.offset + 16] != owner:
            continue
        try:
            v = decode_field(linef, row[linef.offset:linef.offset + linef.size])
            m = max(m, int(v or 0))
        except (ValueError, TypeError):
            pass
    return m



def _table_prefix(db: Database1CD, t: Any, idr: Any) -> bytes:
    for row in db.table_rows(t):
        if row[:1] == b'\x01':
            continue
        raw = row[idr.offset:idr.offset + 16]
        if raw != ZERO16:
            return raw[:4]
    return b'\x00' * 4


def _max_counter(db: Database1CD, t: Any, idr: Any) -> int:
    m = 0
    for row in db.table_rows(t):
        if row[:1] == b'\x01':
            continue
        raw = row[idr.offset:idr.offset + 16]
        if raw != ZERO16:
            m = max(m, struct.unpack('<Q', raw[4:12])[0])
    return m
