"""Выгрузка объекта источника в xlsx-мост (лист «Настройки» + «Данные»).

Формат совместим с макетом настроек .epf «ЗагрузкаДанныхИзТабличногоДокумента»:
шапка R1C5=версия 1.2, R2C1=режим, R3C1=полное имя объекта, R7=первая строка
данных, ниже — маппинг C1–C11; лист «Данные» — заголовок в R1, данные с R2.
Служебные поля не выгружаются; предопределённые записи пропускаются.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .bridge_format import MODE_CATALOG, MODE_REGISTER, ColumnSpec, write_bridge
from .source_8x_file import Database1CD, decode_field, read_metadata
from .typify import KIND_BOOLEAN, KIND_DATE, KIND_NUMBER, KIND_STRING, TypeSpec

# служебные физические поля, не выгружаемые (как xlsx_bridge.SKIP_FIELDS)
_SKIP = {'_IDRREF', '_VERSION', '_MARKED', '_ISMETADATA', '_FOLDER',
         '_ORDERFIELD', '_PREDEFINEDID', '_PARENTIDRREF', '_OWNERIDRREF',
         '_RECORDER', '_LINENO', '_KIND', '_NEWREF'}

_SEARCH_DEFAULT = {'Код': 'Код', 'Наименование': 'Наименование'}


def export_bridge(source_dir: str | Path, obj_fullname: str, out: str | Path,
                  limit: int = 0) -> dict[str, Any]:
    """Справочник/регистр источника -> xlsx-мост; вернуть отчёт.

    Режим определяется по kind метаданных: Справочник -> 0, РегистрСведений
    -> 2 (документы/ТЧ в v1 не выгружаются — BridgeError).
    """
    from .epf_load import BridgeError

    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        raise BridgeError(f'нет файла источника: {cd}')
    md = read_metadata(cd)
    objects = {f"{o['kind']}.{o['name']}": o for o in md.get('objects', [])}
    meta = objects.get(obj_fullname)
    if meta is None:
        raise BridgeError(f'нет объекта источника {obj_fullname!r} '
                          f'в метаданных')
    kind = meta['kind']
    if kind == 'Справочник':
        mode = MODE_CATALOG
    elif kind == 'РегистрСведений':
        mode = MODE_REGISTER
    else:
        raise BridgeError(f'выгрузка {kind!r} не реализована '
                          f'(справочник/регистр сведений)')
    table_name = meta['table']
    attrs = [a for a in (meta.get('attributes') or [])
             if a['field'] not in _SKIP]

    columns: list[ColumnSpec] = []
    for i, a in enumerate(attrs, start=1):
        spec = _spec_from_meta(a)
        is_search = mode == MODE_CATALOG and a['name'] in _SEARCH_DEFAULT
        columns.append(ColumnSpec(
            flag=True, attr=a['name'], search=is_search, type_spec=spec,
            mode='Устанавливать', default='',
            lookup=_SEARCH_DEFAULT.get(a['name'], '') if is_search else '',
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
            out_row: list[Any] = []
            for a in attrs:
                fd = t.fields.get(a['field'])
                if fd is None:
                    out_row.append(None)
                    continue
                v = _decode_safe(fd, row)
                out_row.append(v)
            rows.append(out_row)
            if limit and len(rows) >= limit:
                break

    cfg = type('Cfg', (), {})  # placeholder — не используется
    out_path = Path(out)
    _write(cfg, out_path, mode, obj_fullname, columns, rows)
    return {'ok': True, 'mode': mode, 'object': obj_fullname,
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


def _decode_safe(fd: Any, row: bytes) -> Any:
    try:
        return decode_field(fd, row[fd.offset:fd.offset + fd.size])
    except (IndexError, ValueError, UnicodeDecodeError):
        return None


def _write(_cfg: Any, out_path: Path, mode: int, obj_fullname: str,
           columns: list[ColumnSpec], rows: list[list[Any]]) -> None:
    from .bridge_format import BridgeConfig
    cfg = BridgeConfig(mode=mode, obj_fullname=obj_fullname,
                       first_data_row=2, columns=columns)
    write_bridge(out_path, cfg, rows)
