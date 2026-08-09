"""Массовый перенос через xlsx-мост-конвейер (U27): источник -> intermediate -> load.

Читает map-файл (JSON), для каждого объекта:
- читает таблицу источника (пользовательские записи: не предопределённые, не пустые);
- маппит поля по правилам (fields: целевое имя -> физическое поле источника);
- ссылки: по правилам ref_by_code / parent_as_group / ref_map;
- пишет intermediate JSON (все объекты батчем) и вызывает load_direct.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = 'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1'
TGT = 'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3'


def load_map(path: str) -> list[dict]:
    return json.load(open(path, encoding='utf-8'))['objects']


def read_user_rows(src: str, table: str):
    """Итератор пользовательских записей: dict физическое поле -> значение."""
    from src.onec_converter.source_8x_file import Database1CD, decode_field
    cd = Path(src) / '1Cv8.1CD'
    with Database1CD(cd) as db:
        t = db.tables[table]
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            rec = {}
            for fname, fdef in t.fields.items():
                try:
                    rec[fname] = decode_field(fdef, row[fdef.offset:fdef.offset + fdef.size])
                except (IndexError, ValueError, UnicodeDecodeError):
                    rec[fname] = None
            if rec.get('_ISMETADATA'):
                continue
            if not _has_content(rec):
                continue
            yield rec


def _has_content(rec: dict) -> bool:
    for f in ('_CODE', '_DESCRIPTION', '_DATE_TIME', '_NUMBER', '_PERIOD', '_FLD2407'):
        v = rec.get(f)
        if v not in (None, '', 0):
            return True
    return False


def resolve_ref(src: str, table: str, raw: str | None) -> str | None:
    """GUID -> 'код|наименование' для ключа ссылки (если запись найдена)."""
    if not raw or raw.startswith('00000000-'):
        return None
    from src.onec_converter.source_8x_file import Database1CD
    try:
        raw16 = bytes.fromhex(raw.replace('-', ''))
    except ValueError:
        return None
    if len(raw16) != 16:
        return None
    with Database1CD(Path(src) / '1Cv8.1CD') as db:
        t = db.tables[table]
        idr = t.fields.get('_IDRREF')
        code = t.fields.get('_CODE')
        desc = t.fields.get('_DESCRIPTION')
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            if row[idr.offset:idr.offset + 16] == raw16:
                c = decode_nc_str(row, code) if code else ''
                d = decode_nvc_str(row, desc) if desc else ''
                return f'{c}|{d}' if c else d
    return None


def existing_keys(tgt: str, obj_type: str) -> set[str]:
    """Множество ключей 'код|наименование' существующих записей приёмника
    для целевого типа (чтобы не ссылаться на несуществующие группы)."""
    from src.onec_converter.source_8x_file import Database1CD, read_metadata
    cd = Path(tgt) / '1Cv8.1CD'
    keys: set[str] = set()
    with Database1CD(cd) as db:
        md = read_metadata(str(cd))
        table = None
        for o in md.get('objects', []):
            if f"{o.get('kind')}.{o.get('name')}" == obj_type:
                table = o.get('table')
                break
        if not table or table not in db.tables:
            return keys
        t = db.tables[table]
        idr = t.fields.get('_IDRREF')
        code = t.fields.get('_CODE')
        desc = t.fields.get('_DESCRIPTION')
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            if idr and row[idr.offset:idr.offset + 16] == b'\x00' * 16:
                continue
            c = decode_nc_str(row, code) if code else ''
            d = ''
            if desc:
                try:
                    d = decode_nvc_str(row, desc)
                except Exception:
                    d = ''
            keys.add(f'{c}|{d}')
    return keys


def decode_nvc_str(row: bytes, fd) -> str:
    from src.onec_converter.source_8x_file import decode_nvc
    try:
        return decode_nvc(row[fd.offset:fd.offset + fd.size], fd.null_exists) or ''
    except Exception:
        return ''


def target_field_lens(tgt: str, obj_type: str) -> dict[str, int]:
    """Длины строковых полей целевого объекта (для обрезки)."""
    from src.onec_converter.source_8x_file import read_metadata
    cd = Path(tgt) / '1Cv8.1CD'
    md = read_metadata(str(cd))
    for o in md.get('objects', []):
        if f"{o.get('kind')}.{o.get('name')}" == obj_type:
            return {a.get('name'): a.get('length') or 0
                    for a in o.get('attributes', [])
                    if a.get('type') in ('string', 'NVC', 'NC')}
    return {}


def inn_of(src: str, table: str, guid: str, inn_field: str) -> str | None:
    """ИНН записи источника по GUID (для сопоставления владельцев)."""
    if not guid or guid.startswith('00000000-'):
        return None
    from src.onec_converter.source_8x_file import Database1CD
    try:
        raw16 = bytes.fromhex(guid.replace('-', ''))
    except ValueError:
        return None
    if len(raw16) != 16:
        return None
    with Database1CD(Path(src) / '1Cv8.1CD') as db:
        t = db.tables[table]
        idr = t.fields.get('_IDRREF')
        inn = t.fields.get(inn_field)
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            if row[idr.offset:idr.offset + 16] == raw16:
                if inn:
                    v = decode_nvc_str(row, inn) if inn.type == 'NVC' \
                        else decode_nc_str(row, inn)
                    return v.strip() or None
                return None
    return None


# глобальный кэш: GUID -> условный ИНН (согласованность контрагент/договор)
_FAKE_INN: dict[str, str] = {}
_FAKE_INN_COUNTER = [0]


def fake_inn_for(guid: str) -> str:
    """Условный ИНН 999999NN для записи без ИНН (единожды на GUID)."""
    if guid not in _FAKE_INN:
        _FAKE_INN_COUNTER[0] += 1
        _FAKE_INN[guid] = f'999999{_FAKE_INN_COUNTER[0]:02d}'
    return _FAKE_INN[guid]


def build_objects(spec: dict, tgt_keys: set[str] | None = None,
                  field_lens: dict[str, int] | None = None) -> tuple[list[dict], dict]:
    """Возвращает (объекты intermediate, статистика)."""
    src_table = spec['source_table']
    fields = spec.get('fields', {})
    obj_type = spec['target']
    ref_by_code = spec.get('ref_by_code', {})
    required_refs = spec.get('required_refs', {})
    owner_ref = spec.get('owner_ref')
    inn_field = spec.get('inn_field')
    code_from_inn = spec.get('code_from_inn', False)
    no_number = spec.get('no_number', False)
    force_folder = spec.get('force_folder')
    skip_code_if_dups = spec.get('skip_code_if_dups', False)
    stat = {'read': 0, 'skipped_empty_ref': 0, 'parent_in_root': 0}
    objs = []
    for rec in read_user_rows(SRC, src_table):
        attrs = {}
        refs = {}
        key = []
        rec_guid = str(rec.get('_IDRREF') or '')
        # обязательные ссылки приёмника (например вид номенклатуры)
        for tgt_field, ref_val in required_refs.items():
            if ':' in ref_val:
                refs[tgt_field] = ref_val
        # код из ИНН: контрагенты сопоставляются по ИНН (9 цифр)
        inn = None
        if inn_field:
            v = rec.get(inn_field)
            if v not in (None, '', 0):
                inn = str(v).strip()
        if code_from_inn:
            if not inn or len(inn) != 9:
                # условный ИНН по правилу пользователя (уникальный на GUID)
                inn = fake_inn_for(rec_guid)
            attrs['Код'] = inn
            key = [inn]
        # владелец (составная ссылка источника -> простая приёмника)
        if owner_ref:
            g = rec.get(owner_ref['guid_field'])
            if g and not str(g).startswith('00000000-'):
                if owner_ref.get('by_inn'):
                    o_inn = inn_of(SRC, owner_ref['src_table'], str(g),
                                   inn_field or '_FLD314')
                    if o_inn and len(o_inn) != 9:
                        o_inn = None
                    if not o_inn:
                        # контрагент без ИНН: тот же условный, что и у него
                        o_inn = fake_inn_for(str(g))
                    name = resolve_ref(SRC, owner_ref['src_table'], str(g))
                    nm = name.split('|')[-1] if name else ''
                    refs[owner_ref['tgt_name']] = \
                        f"{owner_ref['tgt_type']}:{o_inn}|{nm}"
                else:
                    owner_key = resolve_ref(SRC, owner_ref['src_table'], g)
                    if owner_key:
                        refs[owner_ref['tgt_name']] = \
                            f"{owner_ref['tgt_type']}:{owner_key}"
        for tgt_name, src_field in fields.items():
            v = rec.get(src_field)
            if tgt_name in ref_by_code and v is not None:
                # ссылка по коду: v — GUID, ищем код валюты в источнике
                code = _ref_code(SRC, '_REFERENCE5', v)
                rb = ref_by_code[tgt_name]
                mapped = rb['map'].get(str(code))
                if mapped:
                    refs[tgt_name] = f"{rb['type']}:{mapped}"
                continue
            if src_field == '_PARENTIDRREF' and v:
                code_name = resolve_ref(SRC, src_table, v)
                if code_name:
                    parent_name = code_name.split('|')[-1]
                    if tgt_keys is not None:
                        # ищем группу приёмника по имени — используем её ключ
                        match = next((k for k in tgt_keys
                                      if k.split('|')[-1] == parent_name), None)
                        if match is None:
                            stat['parent_in_root'] += 1
                            continue
                        refs['Родитель'] = f'{obj_type}:{match}'
                    else:
                        refs['Родитель'] = f'{obj_type}:{code_name}'
            elif v is not None:
                if src_field == '_CODE' and isinstance(v, (int, float)):
                    v = str(int(v))
                if no_number and tgt_name == 'Номер':
                    continue
                if code_from_inn and tgt_name == 'Код':
                    continue  # Код уже установлен из ИНН
                if skip_code_if_dups and tgt_name == 'Код':
                    continue  # 1С назначит код сам (у источника дубли)
                if tgt_name == 'ЭтоГруппа' and force_folder is not None:
                    v = force_folder
                if field_lens and tgt_name in field_lens and isinstance(v, str):
                    ln = field_lens[tgt_name]
                    if ln and len(v) > ln:
                        v = v[:ln]
                        stat['truncated'] = stat.get('truncated', 0) + 1
                attrs[tgt_name] = v
        if tgt_name == 'Период' or 'Период' in attrs or 'Дата' in attrs:
            key = []
        elif 'Код' in attrs:
            key = [str(attrs['Код'])]
            if 'Наименование' in attrs:
                key.append(str(attrs['Наименование']))
        elif code_from_inn:
            key = [str(attrs.get('Код', ''))] if attrs.get('Код') else []
        elif 'Наименование' in attrs:
            key = [str(attrs['Наименование'])]
        objs.append({
            'type': obj_type,
            'id': f'{src_table}:{stat["read"]}',
            'key': key,
            'attributes': attrs,
            'references': refs,
        })
        stat['read'] += 1
    return objs, stat


def _ref_code(src: str, table: str, guid: str) -> str | None:
    """Код записи (для валют — ISO-код) по GUID."""
    from src.onec_converter.source_8x_file import Database1CD
    cd = Path(src) / '1Cv8.1CD'
    with Database1CD(cd) as db:
        t = db.tables[table]
        idr = t.fields['_IDRREF']
        code = t.fields.get('_CODE')
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            raw = row[idr.offset:idr.offset + 16]
            if raw.hex() == guid.replace('-', ''):
                if code:
                    return decode_nc_str(row, code)
                return None
    return None


def decode_nc_str(row: bytes, fd) -> str:
    from src.onec_converter.source_8x_file import decode_nc, decode_nvc
    try:
        if fd.type == 'NVC':
            return decode_nvc(row[fd.offset:fd.offset + fd.size], fd.null_exists) or ''
        return decode_nc(row[fd.offset:fd.offset + fd.size])
    except Exception:
        return ''


def main(map_path: str, workdir: str | None = None, base: str | None = None) -> None:
    from src.onec_converter.intermediate import save_json_batch
    from src.onec_converter.load_8x import load_direct

    global TGT
    if base:
        TGT = base
    specs = load_map(map_path)
    all_objs = []
    total_stat = {}
    tgt_keys_cache: dict[str, set[str]] = {}
    lens_cache: dict[str, dict[str, int]] = {}
    for spec in specs:
        obj_type = spec['target']
        if obj_type not in tgt_keys_cache:
            tgt_keys_cache[obj_type] = existing_keys(TGT, obj_type)
        if obj_type not in lens_cache:
            lens_cache[obj_type] = target_field_lens(TGT, obj_type)
        objs, stat = build_objects(spec, tgt_keys_cache[obj_type],
                                   lens_cache[obj_type])
        all_objs.extend(objs)
        total_stat[spec['target']] = {**stat, 'target_table': spec['source_table']}
        print(f"{spec['target']}: прочитано {stat['read']}", file=sys.stderr)
    out = Path(map_path).with_suffix('.intermediate.json')
    save_json_batch(all_objs, out)
    print(f'intermediate: {out} ({len(all_objs)} объектов)', file=sys.stderr)

    # многоэтапная загрузка по stage: 1 — справочники (родители),
    # 2 — зависимые (договоры с владельцами), 3 — документы
    stages: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for spec in specs:
        st = spec.get('stage', 3 if spec['target'].startswith('Документ.') else 1)
        pass
    for o in all_objs:
        if o['type'].startswith('Документ.'):
            stages[3].append(o)
        elif o['type'] == 'Справочник.ДоговорыКонтрагентов':
            stages[2].append(o)
        else:
            stages[1].append(o)
    wd = Path(workdir) if workdir else None
    cur = TGT
    rep = None
    for i, (name, batch) in enumerate((('stage1', stages[1]), ('stage2', stages[2]),
                                       ('stage3', stages[3]))):
        if not batch:
            continue
        wd_i = (Path(str(wd) + f'_{i + 1}') if wd else None)
        rep = load_direct(cur, batch, workdir=wd_i,
                          verify_after=True)
        print(f'{name}: {len(batch)} объектов -> {rep["copy_path"]}', file=sys.stderr)
        cur = str(Path(rep['copy_path']).parent)
    rep['stat'] = total_stat
    print(json.dumps(rep, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
         sys.argv[3] if len(sys.argv) > 3 else None)
