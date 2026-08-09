"""Фаза 36: SQL-источники (PostgreSQL/MSSQL) — контракт через mock-драйвер."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.sql_source import GenericSqlSource, SqlSourceError, build_sql_source

_CATALOG_TABLES = ['_Reference7', '_InfoRg10', '_AccumRg3']
_CATALOG_COLS = ['table_name', 'column_name']


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    @property
    def description(self):
        return [(c,) for c in _CATALOG_COLS]

    def execute(self, sql, params=None):
        return self

    def fetchall(self):
        return self._rows

    def fetchmany(self, size=1):
        rows = self._rows[:size]
        self._rows = self._rows[size:]
        return rows

    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self.closed = False

    def cursor(self):
        return FakeCursor([(t, '') for t in _CATALOG_TABLES])

    def close(self):
        self.closed = True


class MockDriver:
    @staticmethod
    def connect(dsn):
        return FakeConn()


def test_build_sql_source_with_mock_driver():
    src = build_sql_source('postgres', 'dsn', driver=MockDriver)
    assert isinstance(src, GenericSqlSource)
    tables = src.list_tables()
    assert '_Reference7' in tables
    src.close()


def test_generic_sql_source_list_tables():
    src = GenericSqlSource('postgres', 'dsn', MockDriver)
    tables = src.list_tables()
    assert '_Reference7' in tables and '_InfoRg10' in tables
    assert 'other_t' not in tables  # префикс-фильтр
    src.close()


def test_read_objects_intermediate_format():
    """read_objects возвращает make_object-совместимые объекты."""
    src = GenericSqlSource('mssql', 'dsn', MockDriver)
    objs = list(src.read_objects())
    assert all('type' in o and 'attributes' in o for o in objs)
    src.close()


def test_sql_source_error_on_failed_connect():
    class BadConnect:
        @staticmethod
        def connect(dsn):
            raise ConnectionError('refused')

    src = GenericSqlSource('postgres', 'dsn', BadConnect)
    with pytest.raises(SqlSourceError, match='подключиться'):
        src.list_tables()


def test_extract_cli_has_sql_flags():
    cli = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    assert "'--source-kind'" in cli and "'--source-url'" in cli
    assert "'1cd'" in cli and "'postgres'" in cli and "'mssql'" in cli
