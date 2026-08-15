"""
Интерфейс извлечения данных из 1С: единый API для COM, прямого чтения, JSON и Seed.

ponytail: rung 2 — паттерн из 1C_GPT (backend/.../extractor.py), адаптирован под onec_converter.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Extractor(ABC):
    """Абстрактный источник данных 1С."""

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def read_metadata(self) -> dict[str, Any]: ...

    @abstractmethod
    def extract_to_sqlite(self, sqlite_path: str | Path,
                          limit: int = 0) -> Path: ...


class ComExtractor(Extractor):
    """Извлечение через COM-соединение (текущий метод)."""

    def __init__(self, db_path: str | Path, user: str = '',
                 password: str = ''):
        self._db_path = str(db_path)
        self._user = user or ''
        self._password = password or ''
        self._conn: Any = None

    def connect(self) -> bool:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            v8 = win32com.client.Dispatch('V83.COMConnector')
            conn_str = f'File="{self._db_path}";'
            if self._user:
                conn_str += f' Usr="{self._user}";'
                if self._password:
                    conn_str += f' Pwd="{self._password}";'
            self._conn = v8.Connect(conn_str)
            return True
        except Exception:
            pythoncom.CoUninitialize()
            return False

    def disconnect(self) -> None:
        self._conn = None
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def read_metadata(self) -> dict[str, Any]:
        from .source_8x_file import read_metadata
        cd = Path(self._db_path) / '1Cv8.1CD'
        if not cd.is_file():
            cd = Path(self._db_path)  # может быть прямым путём к 1CD
        return read_metadata(str(cd))

    def extract_to_sqlite(self, sqlite_path: str | Path,
                          limit: int = 0) -> Path:
        from .sqlite_extract import extract_to_sqlite
        return extract_to_sqlite(self._db_path, sqlite_path, limit=limit)


class DirectExtractor(Extractor):
    """Прямое чтение 1CD через onec_dtools (без платформы 1С)."""

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db: Any = None
        self._file: Any = None

    def connect(self) -> bool:
        try:
            from onec_dtools import DatabaseReader
            cd = self._db_path
            if cd.is_dir():
                cd = cd / '1Cv8.1CD'
            if not cd.is_file():
                return False
            self._file = open(str(cd), 'rb')
            self._db = DatabaseReader(self._file)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def disconnect(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
        self._db = None

    def read_metadata(self) -> dict[str, Any]:
        if not self._db:
            raise RuntimeError('Not connected')
        # Извлекаем метаданные из DBNames + _objects таблицы
        objects: list[dict[str, Any]] = []
        for table_name, table in self._db.tables.items():
            if table_name.startswith('_'):
                continue
            # Определяем тип объекта по префиксу таблицы
            kind = _guess_kind(table_name)
            if kind:
                objects.append({
                    'kind': kind,
                    'name': table_name,
                    'table': table_name,
                })
        return {'objects': objects, 'version': str(getattr(self._db, 'version', ''))}

    def extract_to_sqlite(self, sqlite_path: str | Path,
                          limit: int = 0) -> Path:
        import sqlite3
        if not self._db:
            raise RuntimeError('Not connected')
        out = Path(sqlite_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(out))
        con.execute('CREATE TABLE IF NOT EXISTS _objects '
                    '(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, '
                    'name TEXT, table_name TEXT, category TEXT)')
        obj_id = 0
        for table_name, table in self._db.tables.items():
            if table_name.startswith('_'):
                continue
            kind = _guess_kind(table_name)
            if not kind:
                continue
            obj_id += 1
            con.execute(
                'INSERT INTO _objects (id, kind, name, table_name, category) '
                'VALUES (?, ?, ?, ?, ?)',
                (obj_id, kind, f'{kind}.{table_name}', table_name, 'user'))
            # Читаем данные
            rows = list(table)
            if not rows:
                continue
            sample = rows[0].as_dict(read_blobs=False) if hasattr(rows[0], 'as_dict') else {}
            if not sample:
                continue
            cols = list(sample.keys())
            col_defs = ', '.join(f'[{c}] TEXT' for c in cols)
            con.execute(f'CREATE TABLE IF NOT EXISTS [{kind}.{table_name}] ({col_defs})')
            placeholders = ', '.join(['?'] * len(cols))
            count = 0
            for row in table:
                if limit and count >= limit:
                    break
                if hasattr(row, 'as_dict'):
                    d = row.as_dict(read_blobs=False)
                    vals = [str(d.get(c, '')) if d.get(c) is not None else None
                            for c in cols]
                else:
                    vals = [str(getattr(row, c, '')) if hasattr(row, c) else None
                            for c in cols]
                con.execute(
                    f'INSERT INTO [{kind}.{table_name}] VALUES ({placeholders})',
                    vals)
                count += 1
        con.commit()
        con.close()
        return out


class SeedExtractor(Extractor):
    """Синтетические данные для тестов (без 1С)."""

    def __init__(self, objects: list[dict[str, Any]] | None = None):
        self._objects = objects or [
            {'kind': 'Справочник', 'name': 'Тест', 'table': '_Reference1',
             'attributes': [
                 {'name': 'Код', 'field': '_CODE', 'type': 'NVC', 'length': 9},
                 {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'NVC', 'length': 100},
             ]},
        ]

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def read_metadata(self) -> dict[str, Any]:
        return {'objects': self._objects}

    def extract_to_sqlite(self, sqlite_path: str | Path,
                          limit: int = 0) -> Path:
        import sqlite3
        out = Path(sqlite_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(out))
        con.execute('CREATE TABLE IF NOT EXISTS _objects '
                    '(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, '
                    'name TEXT, table_name TEXT, category TEXT)')
        for i, obj in enumerate(self._objects):
            full_name = f"{obj['kind']}.{obj['name']}"
            con.execute(
                'INSERT INTO _objects (id, kind, name, table_name, category) '
                'VALUES (?, ?, ?, ?, ?)',
                (i + 1, obj['kind'], full_name, obj.get('table', ''), 'user'))
            attrs = obj.get('attributes', [])
            cols = ['_IDRREF'] + [a['field'] for a in attrs]
            col_defs = ', '.join(f'[{c}] TEXT' for c in cols)
            con.execute(f'CREATE TABLE IF NOT EXISTS [{full_name}] ({col_defs})')
            # 3 тестовые строки
            for j in range(3):
                vals = [f'guid-{i}-{j}']  # _IDRREF
                for a in attrs:
                    vals.append(f'{a["name"]}_{j}')
                placeholders = ', '.join(['?'] * len(cols))
                con.execute(
                    f'INSERT INTO [{full_name}] VALUES ({placeholders})', vals)
        con.commit()
        con.close()
        return out


def _guess_kind(table_name: str) -> str:
    """Определить тип объекта по префиксу имени таблицы."""
    t = table_name.lower()
    if t.startswith('_reference'):
        return 'Справочник'
    if t.startswith('_document'):
        return 'Документ'
    if t.startswith('_inforg') or t.startswith('_informationregister'):
        return 'РегистрСведений'
    if t.startswith('_accumrg') or t.startswith('_accumulationregister'):
        return 'РегистрНакопления'
    if t.startswith('_accrg'):
        return 'РегистрБухгалтерии'
    return ''


def create_extractor(source: str = 'com', **kwargs: Any) -> Extractor:
    """Фабрика: создать экстрактор по имени."""
    if source == 'com':
        return ComExtractor(kwargs.get('db_path', ''))
    elif source == 'direct':
        return DirectExtractor(kwargs.get('db_path', ''))
    elif source == 'seed':
        return SeedExtractor(kwargs.get('objects'))
    elif source == 'json':
        return ComExtractor(kwargs.get('db_path', ''))  # fallback
    raise ValueError(f'Unknown extractor: {source}')
