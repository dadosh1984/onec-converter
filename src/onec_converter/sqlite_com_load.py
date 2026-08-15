"""Загрузка данных из SQLite в 1С через COM-соединение.

Быстрее xlsx-моста (один запуск 1С) и не ломает индексы (штатный API).
ponytail: rung 5 — win32com + существующий sqlite_load.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

# Стандартный маппинг технических имён полей 1С → имена реквизитов
_FIELD_NAME_MAP: dict[str, str] = {
    '_CODE': 'Код',
    '_DESCRIPTION': 'Наименование',
    '_DATE_TIME': 'Дата',
    '_NUMBER': 'Номер',
    '_POSTED': 'Проведен',
    '_FOLDER': 'ЭтоГруппа',
    '_MARKED': 'ПометкаУдаления',
    '_PERIOD': 'Период',
    '_LINENO': 'НомерСтроки',
    '_ACTIVE': 'Активность',
}

_SKIP_COLS: set[str] = {
    '_IDRREF', '_VERSION', '_MARKED', '_ISMETADATA', '_ORDERFIELD', '_KIND',
    '_PREDEFINEDID', '_RECORDERTREF', '_TYPE', '_RTREF', '_RRREF',
    '_PARENTIDRREF', '_RECORDERRREF',
}

# Паттерны колонок, которые нельзя маппить на реквизиты 1С
_SKIP_PATTERNS: tuple[str, ...] = ('_FLD', '_TYPE', '_RTREF', '_RRREF', '_RRef', 'RREF')


def load_via_com(
    sqlite_path: str | Path,
    target_dir: str | Path,
    max_objects: int = 0,
) -> dict[str, Any]:
    """Загрузить данные из SQLite в копию 1CD через COM-соединение.

    Args:
        sqlite_path: путь к .sqlite (после apply_mapping)
        target_dir: каталог с 1Cv8.1CD (копия приёмника)
        max_objects: лимит объектов (0 = все)

    Returns:
        {'ok': True/False, 'total': N, 'created': N, 'errors': [...]}
    """
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()

    try:
        v8 = win32com.client.Dispatch('V83.COMConnector')
        conn_str = f'File="{target_dir}";'
        conn = v8.Connect(conn_str)
    except Exception as exc:
        pythoncom.CoUninitialize()
        return {'ok': False, 'error': f'Не удалось подключиться к 1С: {exc}'}

    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row

    has_mapping = con.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='_object_mapping'"
    ).fetchone()[0]

    if has_mapping:
        mappings = con.execute(
            "SELECT id, source_name, target_name FROM _object_mapping "
            "WHERE status='ready' ORDER BY id"
        ).fetchall()
    else:
        mappings = con.execute(
            "SELECT id, name AS source_name, name AS target_name "
            "FROM _objects WHERE category='user' ORDER BY id"
        ).fetchall()

    if max_objects and len(mappings) > max_objects:
        mappings = mappings[:max_objects]

    report_objects: list[dict[str, Any]] = []
    total_created = 0
    errors: list[dict[str, Any]] = []

    for om_id, src_name, tgt_name in mappings:
        try:
            rows = con.execute(f'SELECT * FROM [{src_name}]').fetchall()
        except sqlite3.OperationalError:
            errors.append({'obj': src_name, 'error': 'таблица не найдена в SQLite'})
            continue

        if not rows:
            continue

        cols = [d[1] for d in con.execute(f'PRAGMA table_info([{src_name}])').fetchall()]
        
        # Читаем _field_mapping — пишем ТОЛЬКО матчащиеся поля
        field_map_cols = _load_field_mapping(con, om_id)
        if field_map_cols is not None:
            # Есть явный маппинг: используем только ready-поля
            write_cols = [c for c in cols
                         if c in field_map_cols
                         and c not in _SKIP_COLS
                         and not any(c.startswith(p) for p in _SKIP_PATTERNS)
                         and not c.endswith('RREF')]
        else:
            # Нет _field_mapping: фильтруем как раньше
            write_cols = [c for c in cols
                         if c not in _SKIP_COLS
                         and not any(c.startswith(p) for p in _SKIP_PATTERNS)
                         and not c.endswith('RREF')]
        
        if not write_cols:
            errors.append({'obj': src_name, 'error': 'нет пригодных колонок для записи'})
            continue
        
        # Маппинг технических имён → реквизиты 1С
        col_map = {c: _FIELD_NAME_MAP.get(c, c) for c in write_cols}

        created = 0
        reused = 0
        for row in rows:
            try:
                kind, short_name = _split_name(tgt_name)
                if short_name == 'Номенклатура':
                    search_name = row['_DESCRIPTION'] if '_DESCRIPTION' in row.keys() else ''
                    search_code = row['_CODE'] if '_CODE' in row.keys() else ''
                    obj, was_created = _create_or_write_nomenclature(conn, short_name, search_name, search_code)
                else:
                    search_field = write_cols[0]
                    search_value = row[search_field]
                    obj, item = _create_or_find_with_item(conn, kind, short_name, col_map[search_field],
                                          str(search_value) if search_value is not None else '')
                    was_created = obj is not None
                if obj is None:
                    errors.append({'obj': src_name, 'error': f'не удалось создать {tgt_name}'})
                    continue

                for c in write_cols:
                    val = row[c]
                    if val is not None:
                        try:
                            setattr(obj, col_map[c], val)
                        except Exception:
                            pass
                try:
                    obj.Write()
                except Exception:
                    # Любая ошибка Write — возможно, дубликат. Пробуем найти и обновить.
                    try:
                        if item is not None:
                            code_val = str(search_val) if search_val else ''
                            existing = item.НайтиПоКоду(code_val) if code_val else None
                            if existing is None:
                                existing = item.НайтиПоНаименованию(code_val)
                            if existing is not None and not getattr(existing, 'Пустая', lambda: True)():
                                for c in write_cols:
                                    val2 = row[c]
                                    if val2 is not None:
                                        try:
                                            setattr(existing, col_map[c], val2)
                                        except Exception:
                                            pass
                                existing.Write()
                                reused += 1
                                continue
                    except Exception:
                        pass
                    raise
                if was_created:
                    created += 1
                else:
                    reused += 1
            except Exception as exc:
                errors.append({'obj': src_name, 'error': str(exc)})

        report_objects.append({'source': src_name, 'target': tgt_name, 'created': created, 'reused': reused})
        total_created += created

    con.close()
    pythoncom.CoUninitialize()

    return {
        'ok': True,
        'total': len(report_objects),
        'created': total_created,
        'objects': report_objects,
        'errors': errors,
    }


def _split_name(name: str) -> tuple[str, str]:
    if '.' in name:
        kind, short_name = name.split('.', 1)
        return kind, short_name
    return 'Справочник', name


def _create_or_find(v8, cat: str, name: str, field: str, value: str):
    """Найти или создать объект в 1С через COM."""
    obj, _item = _create_or_find_with_item(v8, cat, name, field, value)
    return obj


def _create_or_find_with_item(v8, cat: str, name: str, field: str, value: str):
    """Найти или создать объект. Возвращает (obj, item_ref) для повторного поиска."""
    try:
        if cat == 'Справочник':
            catalog = getattr(v8, 'Справочники')
            item = getattr(catalog, name)
            ref = item.НайтиПоНаименованию(value)
            if ref is None or getattr(ref, 'Пустая', lambda: True)():
                obj = item.СоздатьЭлемент()
                setattr(obj, field, value)
                return obj, item
            return ref, item
        if cat == 'Документ':
            docs = getattr(v8, 'Документы')
            item = getattr(docs, name)
            obj = item.СоздатьДокумент()
            # Документы должны иметь Дату и быть проведены для видимости
            try:
                import datetime
                setattr(obj, 'Дата', datetime.date.today())
            except Exception:
                pass
            try:
                setattr(obj, 'Проведен', True)
            except Exception:
                pass
            return obj, item
    except Exception:
        return None, None
    return None, None


def _create_or_write_nomenclature(v8, name: str, search_name: str, search_code: str):
    try:
        item = getattr(getattr(v8, 'Справочники'), name)
        existing = _find_nomenclature_in_item(item, search_name, search_code)
        if existing is not None:
            existing.Write()
            return existing, False

        if search_code:
            ref = item.НайтиПоКоду(search_code)
            if ref is not None and not getattr(ref, 'Пустая', lambda: True)():
                ref.Write()
                return ref, False

        obj = item.СоздатьЭлемент()
        if search_name:
            setattr(obj, 'Наименование', search_name)
        obj.Write()
        return obj, True
    except Exception:
        return None, False


def _find_nomenclature_in_item(item, search_name: str, search_code: str):
    for obj in getattr(item, 'items', []):
        if search_name and obj.values.get('Наименование') == search_name:
            return obj
        if search_code and obj.values.get('Код') == search_code:
            return obj
    return None


def _create_or_find_nomenclature(v8, name: str, search_name: str, search_code: str):
    return _create_or_write_nomenclature(v8, name, search_name, search_code)


# ---------------------------------------------------------------------------
# Точечный COM-маппинг одного объекта (sqlite-com-one-object-map)
# ponytail: rung 2 — использует существующий COM-коннектор
# ---------------------------------------------------------------------------


def load_one_object(
    sqlite_path: str | Path,
    target_dir: str | Path,
    obj_name: str,
    field_map: dict[str, str] | None = None,
    search_fields: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Записать ОДИН объект через COM с явным маппингом полей.

    Args:
        sqlite_path: путь к .sqlite с таблицей объекта
        target_dir: каталог с 1Cv8.1CD (копия приёмника)
        obj_name: полное имя объекта ('Справочник.Номенклатура')
        field_map: маппинг 'колонка_SQLite' → 'реквизит_1С' (None = auto)
        search_fields: поля для поиска существующего объекта
        dry_run: True = только проверка соединения, без записи

    Returns:
        {'ok', 'created': bool, 'obj_name', 'fields_written': [...], 'errors': [...]}
    """
    import pythoncom
    import win32com.client

    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row

    try:
        rows = con.execute(f'SELECT * FROM [{obj_name}]').fetchall()
    except sqlite3.OperationalError:
        con.close()
        return {'ok': False, 'error': f'таблица {obj_name!r} не найдена в SQLite'}

    if not rows:
        con.close()
        return {'ok': True, 'created': False, 'obj_name': obj_name,
                'reason': 'нет данных в SQLite', 'fields_written': []}

    cols = [d[1] for d in con.execute(f'PRAGMA table_info([{obj_name}])').fetchall()]
    con.close()

    # Строим маппинг: колонка SQLite → реквизит 1С
    if field_map is None:
        # auto: все колонки кроме _
        field_map = {c: c for c in cols if not c.startswith('_')}

    search = search_fields or ([list(field_map.keys())[0]] if field_map else [])

    pythoncom.CoInitialize()
    try:
        v8 = win32com.client.Dispatch('V83.COMConnector')
        conn = v8.Connect(f'File="{target_dir}";')
    except Exception as exc:
        pythoncom.CoUninitialize()
        return {'ok': False, 'error': f'COM connect: {exc}'}

    if dry_run:
        pythoncom.CoUninitialize()
        return {'ok': True, 'dry_run': True, 'obj_name': obj_name,
                'field_map': field_map, 'search_fields': search}

    row = rows[0]
    kind, short_name = _split_name(obj_name)
    fields_written: list[str] = []
    errors: list[dict[str, Any]] = []

    try:
        # Поиск существующего по первому search-полю
        search_col = search[0]
        search_attr = field_map.get(search_col, search_col)
        search_val = row[search_col]

        obj = _create_or_find(conn, kind, short_name, search_attr,
                             str(search_val) if search_val is not None else '')
        was_created = obj is not None
        if obj is None:
            pythoncom.CoUninitialize()
            return {'ok': False, 'error': f'не удалось создать {obj_name}'}

        # Явный маппинг колонок → реквизитов
        for sqlite_col, attr_1c in field_map.items():
            if sqlite_col not in row.keys():
                continue
            val = row[sqlite_col]
            if val is None:
                continue
            try:
                setattr(obj, attr_1c, val)
                fields_written.append(attr_1c)
            except Exception as exc:
                errors.append({'field': attr_1c, 'value': str(val)[:100],
                              'error': str(exc)})

        obj.Write()
    except Exception as exc:
        pythoncom.CoUninitialize()
        return {'ok': False, 'error': str(exc)}

    pythoncom.CoUninitialize()
    return {
        'ok': True,
        'created': was_created,
        'obj_name': obj_name,
        'fields_written': fields_written,
        'field_map': field_map,
        'errors': errors,
    }


def verify_object(
    sqlite_path: str | Path,
    target_dir: str | Path,
    obj_name: str,
    field_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Smoke-test: записать один объект → прочитать обратно → сравнить поля.

    Returns:
        {'ok', 'written': [...], 'verified': [...], 'mismatches': [...], 'errors': [...]}
    """
    # 1. Записать
    write_result = load_one_object(
        sqlite_path, target_dir, obj_name, field_map=field_map)

    if not write_result.get('ok'):
        return {'ok': False, 'stage': 'write',
                'error': write_result.get('error', 'write failed')}

    if write_result.get('dry_run'):
        return {'ok': True, 'stage': 'dry_run',
                'message': 'dry run — подключение работает'}

    # 2. Прочитать обратно
    import pythoncom
    import win32com.client

    con = sqlite3.connect(str(sqlite_path))
    con.row_factory = sqlite3.Row
    try:
        src_rows = con.execute(f'SELECT * FROM [{obj_name}]').fetchall()
    except sqlite3.OperationalError:
        con.close()
        return {'ok': False, 'stage': 'read_sqlite',
                'error': f'таблица {obj_name!r} не найдена'}
    con.close()

    if not src_rows:
        return {'ok': False, 'stage': 'read_sqlite',
                'error': 'нет данных для верификации'}

    src_row = src_rows[0]
    fm = field_map or {c: c for c in src_row.keys() if not c.startswith('_')}

    pythoncom.CoInitialize()
    try:
        v8 = win32com.client.Dispatch('V83.COMConnector')
        conn = v8.Connect(f'File="{target_dir}";')
    except Exception as exc:
        pythoncom.CoUninitialize()
        return {'ok': False, 'stage': 'com_connect', 'error': str(exc)}

    kind, short_name = _split_name(obj_name)
    mismatches: list[dict[str, Any]] = []
    verified: list[str] = []

    try:
        # Поиск записанного объекта
        search_col = list(fm.keys())[0]
        search_val = src_row[search_col]

        catalog = getattr(conn, 'Справочники' if kind == 'Справочник' else 'Документы')
        item = getattr(catalog, short_name)
        found = item.НайтиПоНаименованию(str(search_val) if search_val else '')

        if found is None or getattr(found, 'Пустая', lambda: True)():
            pythoncom.CoUninitialize()
            return {'ok': False, 'stage': 'verify',
                    'error': f'объект не найден после записи: {search_val}'}

        # Сравнение полей
        for sqlite_col, attr_1c in fm.items():
            if sqlite_col not in src_row.keys():
                continue
            expected = src_row[sqlite_col]
            try:
                actual = getattr(found, attr_1c)
            except Exception:
                mismatches.append({'field': attr_1c, 'sqlite_col': sqlite_col,
                                  'expected': str(expected)[:100], 'error': 'не удалось прочитать'})
                continue

            if str(expected) != str(actual) if expected is not None else actual is not None:
                mismatches.append({'field': attr_1c, 'sqlite_col': sqlite_col,
                                  'expected': str(expected)[:100],
                                  'actual': str(actual)[:100]})
            else:
                verified.append(attr_1c)

    except Exception as exc:
        pythoncom.CoUninitialize()
        return {'ok': False, 'stage': 'verify', 'error': str(exc)}

    pythoncom.CoUninitialize()
    return {
        'ok': True,
        'obj_name': obj_name,
        'written': write_result.get('fields_written', []),
        'verified': verified,
        'mismatches': mismatches,
    }


def _load_field_mapping(con: Any, om_id: int) -> set[str] | None:
    """Загрузить список ready source_field для object_mapping_id.
    Возвращает None если _field_mapping отсутствует."""
    has_fm = con.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='_field_mapping'"
    ).fetchone()[0]
    if not has_fm:
        return None
    rows = con.execute(
        'SELECT source_field FROM _field_mapping '
        'WHERE object_mapping_id=? AND status=? AND target_field IS NOT NULL',
        (om_id, 'ready')
    ).fetchall()
    if not rows:
        return None
    return {r[0] for r in rows}
