"""Выгрузка объекта источника в xlsx-мост (лист «Настройки» + «Данные»).

Формат совместим с макетом настроек .epf «ЗагрузкаДанныхИзТабличногоДокумента»:
шапка R1C5=версия 1.2, R2C1=режим, R3C1=полное имя объекта, R7=первая строка
данных, ниже — маппинг C1–C11; лист «Данные» — заголовок в R1, данные с R2.
Служебные поля не выгружаются; предопределённые записи пропускаются.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .bridge_format import MODE_CATALOG, MODE_REGISTER, MODE_TABLE, ColumnSpec, write_bridge
from .source_8x_file import Database1CD, decode_field, read_metadata
from .typify import KIND_BOOLEAN, KIND_DATE, KIND_NUMBER, KIND_STRING, TypeSpec

# служебные физические поля, не выгружаемые (как xlsx_bridge.SKIP_FIELDS)
_SKIP = {'_IDRREF', '_VERSION', '_MARKED', '_ISMETADATA', '_FOLDER',
         '_ORDERFIELD', '_PREDEFINEDID', '_PARENTIDRREF', '_OWNERIDRREF',
         '_RECORDER', '_LINENO', '_KIND', '_NEWREF'}

_SEARCH_DEFAULT = {'Код': 'Код', 'Наименование': 'Наименование'}

# документ: поиск по номеру; _NUMBERPREFIX — служебное (префикс номера)
_SEARCH_DOC = {'Номер': 'Номер'}
_SKIP_DOC = {'_NUMBERPREFIX'}


def _split_fullname(obj_fullname: str) -> tuple[str, str, str]:
    """'Справочник.Х' | 'Документ.Х' | 'Документ.Х.ТЧ.<_VT...>' -> (kind, name, vt)."""
    parts = obj_fullname.split('.')
    if len(parts) == 4 and parts[2] == 'ТЧ':
        return parts[0], parts[1], parts[3]
    if len(parts) >= 2:
        return parts[0], parts[1], ''
    return obj_fullname, '', ''


def export_bridge(source_dir: str | Path, obj_fullname: str, out: str | Path,
                  limit: int = 0) -> dict[str, Any]:
    """Справочник/документ/регистр/ТЧ источника -> xlsx-мост; отчёт.

    Режим по kind: Справочник/Документ -> 0 (поиск по Код/Номер),
    РегистрСведений -> 2, ТЧ документа ('Документ.Х.ТЧ.<таблица>') -> 1.
    """
    from .epf_load import BridgeError

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        raise BridgeError(f'нет файла источника: {cd}')
    kind, name, vt = _split_fullname(obj_fullname)
    if kind == 'Документ' and vt:
        return _export_vt(cd, obj_fullname, f'{kind}.{name}', vt, out, limit)
    md = read_metadata(cd)
    objects = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}
    meta = objects.get(obj_fullname)
    if meta is None:
        raise BridgeError(f'нет объекта источника {obj_fullname!r} '
                          f'в метаданных')
    kind = meta['kind']
    if kind == 'Документ':
        mode = MODE_CATALOG
        search_map = _SEARCH_DOC
    elif kind == 'Справочник':
        mode = MODE_CATALOG
        search_map = _SEARCH_DEFAULT
    elif kind == 'РегистрСведений':
        mode = MODE_REGISTER
        search_map = {}
    else:
        raise BridgeError(f'выгрузка {kind!r} не реализована '
                          f'(справочник/документ/регистр сведений/ТЧ)')
    table_name = meta['table']
    attrs = [a for a in (meta.get('attributes') or [])
             if a['field'] not in _SKIP and a['field'] not in _SKIP_DOC]

    columns: list[ColumnSpec] = []
    for i, a in enumerate(attrs, start=1):
        spec = _spec_from_meta(a)
        is_search = mode == MODE_CATALOG and a['name'] in search_map
        columns.append(ColumnSpec(
            flag=True, attr=a['name'], search=is_search, type_spec=spec,
            mode='Устанавливать', default='',
            lookup=search_map.get(a['name'], '') if is_search else '',
            owner_ref='', type_ref='', type_elem=0, col_num=i))

    rows: list[list[Any]] = []
    with Database1CD(cd) as db:
        t = db.tables.get(table_name)
        if t is None:
            raise BridgeError(f'нет таблицы {table_name!r} в источнике')
        for row in db.table_rows(t):
            if row[:1] == b'\x01' or (t.fields.get('_ISMETADATA')
                                      and row[t.fields['_ISMETADATA'].offset] != 0):
                continue
            idr = t.fields.get('_IDRREF')
            if idr is not None and row[idr.offset:idr.offset + 16] == b'\x00' * 16:
                continue  # служебная строка (пустая ссылка)
            out_row: list[Any] = []
            for a in attrs:
                fd = t.fields.get(a['field'])
                if fd is None:
                    out_row.append(None)
                    continue
                out_row.append(_decode_safe(fd, row))
            rows.append(out_row)
            if limit and len(rows) >= limit:
                break

    _write(out_path := Path(out), mode, obj_fullname, columns, rows)
    return {'ok': True, 'mode': mode, 'object': obj_fullname,
            'rows': len(rows), 'out': str(out_path)}


def _export_vt(cd: Path, obj_fullname: str, owner_name: str, vt_name: str,
               out: str | Path, limit: int = 0) -> dict[str, Any]:
    """ТЧ документа -> мост режима 1: колонки поиска владельца (Номер) +
    реквизиты VT-таблицы. Возвращает отчёт как export_bridge."""
    from .epf_load import BridgeError

    md = read_metadata(cd)
    objects = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}
    owner = objects.get(owner_name)
    if owner is None:
        raise BridgeError(f'нет документа-владельца {owner_name!r} в метаданных')
    owner_attrs = {a['name']: a for a in (owner.get('attributes') or [])}

    with Database1CD(cd) as db:
        vt = db.tables.get(vt_name)
        if vt is None:
            raise BridgeError(f'нет табличной части {vt_name!r} в источнике')
        owner_t = db.tables.get(owner['table'])
        if owner_t is None:
            raise BridgeError(f'нет таблицы {owner["table"]!r} в источнике')

        # колонки: поиск владельца (Номер, если есть) + реквизиты VT
        columns: list[ColumnSpec] = []
        col_no = 0
        for name in ('Номер', '_DATE_TIME'):
            if name in owner_attrs:
                col_no += 1
                a = owner_attrs[name]
                columns.append(ColumnSpec(
                    flag=True, attr=a['name'], search=True, type_spec=_spec_from_meta(a),
                    mode='Устанавливать', default='',
                    lookup=a['name'] if a['name'] == 'Номер' else '',
                    owner_ref='', type_ref='', type_elem=0, col_num=col_no))
        linef = next((f for f in vt.fields.values()
                      if f.name.upper().startswith('_LINENO')), None)
        for fname, fd in sorted(vt.fields.items()):
            if fname == '_KEYFIELD' or fname == linef.name if linef else False:
                continue
            if fname.endswith('IDRREF') and len(fname) > len('_IDRREF'):
                continue  # родитель
            col_no += 1
            columns.append(ColumnSpec(
                flag=True, attr=fname, search=False,
                type_spec=_spec_from_field(fd),
                mode='Устанавливать', default='', lookup='',
                owner_ref='', type_ref='', type_elem=0, col_num=col_no))

        # строки: для каждого документа — строки его VT (Номер + реквизиты)
        rows: list[list[Any]] = []
        par: Any = next((f for f in vt.fields.values()
                        if f.name.endswith('IDRREF')
                        and len(f.name) > len('_IDRREF')), None)
        owner_vals: dict[str, Any] = {}
        for drow in db.table_rows(owner_t):
            if drow[:1] == b'\x01':
                continue
            owner_id = drow[owner_t.fields['_IDRREF'].offset:
                            owner_t.fields['_IDRREF'].offset + 16]
            if owner_id == b'\x00' * 16:
                continue
            for name in ('Номер', '_DATE_TIME'):
                if name in owner_attrs:
                    ofd: Any = owner_t.fields.get(owner_attrs[name]['field'])
                    owner_vals[name] = (_decode_safe(ofd, drow)
                                        if ofd is not None else None)
            for vrow in db.table_rows(vt):
                if vrow[:1] == b'\x01':
                    continue
                if par is not None and vrow[par.offset:par.offset + 16] != owner_id:
                    continue
                out_row: list[Any] = []
                for c in columns:
                    if c.attr in owner_vals:
                        out_row.append(owner_vals[c.attr])
                    else:
                        vfd: Any = vt.fields.get(c.attr)
                        out_row.append(_decode_safe(vfd, vrow)
                                       if vfd is not None else None)
                rows.append(out_row)
                if limit and len(rows) >= limit:
                    break
            if limit and len(rows) >= limit:
                break

    _write(out_path := Path(out), MODE_TABLE, obj_fullname, columns, rows)
    return {'ok': True, 'mode': MODE_TABLE, 'object': obj_fullname,
            'rows': len(rows), 'out': str(out_path)}


def _spec_from_meta(a: dict[str, Any]) -> TypeSpec:
    t = a['type']
    if t == 'number':
        return TypeSpec(kinds=(KIND_NUMBER,), num_length=a.get('length', 0),
                        num_precision=a.get('precision', 0))
    if t == 'bool':
        return TypeSpec(kinds=(KIND_BOOLEAN,))
    if t == 'date':
        return TypeSpec(kinds=(KIND_DATE,), date_parts='datetime')
    return TypeSpec(kinds=(KIND_STRING,))


def _spec_from_field(fd: Any) -> TypeSpec:
    """TypeSpec по физическому полю VT-таблицы (тип FieldDef)."""
    ft = fd.type
    if ft in ('NVC', 'NC'):
        return TypeSpec(kinds=(KIND_STRING,))
    if ft in ('N', 'NT', 'I'):
        return TypeSpec(kinds=(KIND_NUMBER,), num_length=fd.length,
                        num_precision=fd.precision)
    if ft == 'DT':
        return TypeSpec(kinds=(KIND_DATE,), date_parts='datetime')
    if ft == 'L':
        return TypeSpec(kinds=(KIND_BOOLEAN,))
    return TypeSpec(kinds=(KIND_STRING,))  # RV/B — GUID-строка


_CONTROL = dict.fromkeys(range(32))  # 0x00-0x1F -> удалить из строк (openpyxl)


def _decode_safe(fd: Any, row: bytes) -> Any:
    try:
        v = decode_field(fd, row[fd.offset:fd.offset + fd.size])
        if isinstance(v, bytes):
            return None  # бинарные/BLOB-значения в xlsx-мост не выгружаем
        if isinstance(v, str) and v:
            v = v.translate(_CONTROL)
        return v
    except (IndexError, ValueError, UnicodeDecodeError):
        return None


def _write(out_path: Path, mode: int, obj_fullname: str,
           columns: list[ColumnSpec], rows: list[list[Any]]) -> None:
    from .bridge_format import BridgeConfig
    cfg = BridgeConfig(mode=mode, obj_fullname=obj_fullname,
                       first_data_row=2, columns=columns)
    write_bridge(out_path, cfg, rows)
