"""Фаза 43: SQL-источники до production-grade — connect_timeout, потоковая
fetchmany, интеграционный тест на реальном PostgreSQL (env-gated)."""
from __future__ import annotations

import os

import pytest

from onec_converter.sql_source import GenericSqlSource, SqlSourceError


# ---- connect_timeout: не зависать на недоступном сервере ----
def test_connect_passes_timeout_to_driver():
    seen: dict[str, object] = {}

    class TimedDriver:
        @staticmethod
        def connect(dsn, **kw):
            seen.update(kw)
            class C:
                def cursor(self):
                    class Cur:
                        def execute(self, *a): pass
                        def close(self): pass
                    return Cur()
                def close(self): pass
            return C()

    src = GenericSqlSource('postgres', 'dsn', TimedDriver, connect_timeout=7)
    src._connect()
    assert seen.get('connect_timeout') == 7
    src.close()

    seen.clear()
    src2 = GenericSqlSource('mssql', 'dsn', TimedDriver, connect_timeout=9)
    src2._connect()
    assert seen.get('timeout') == 9
    src2.close()


def test_connect_falls_back_without_timeout_kwarg():
    """Драйвер без поддержки таймаута (мок) — подключается по dsn."""

    class PlainDriver:
        @staticmethod
        def connect(dsn):
            class C:
                def cursor(self): return None
                def close(self): pass
            return C()

    src = GenericSqlSource('postgres', 'dsn', PlainDriver)
    assert src._connect() is not None
    src.close()


def test_connect_timeout_raises_sql_error():
    class SlowFail:
        @staticmethod
        def connect(dsn, **kw):
            raise ConnectionError('timeout')

    src = GenericSqlSource('postgres', 'dsn', SlowFail, connect_timeout=1)
    with pytest.raises(SqlSourceError, match='не удалось подключиться'):
        src._connect()


# ---- потоковая выборка: fetchmany порциями, без fetchall ----
def test_fetch_rows_streams_in_batches():
    rows = [(i,) for i in range(5)]  # кортежи, как реальный DB-курсор
    calls: list[int] = []

    class BatchDriver:
        @staticmethod
        def connect(dsn):
            class C:
                def cursor(self, name=None):
                    class Cur:
                        def __init__(self):
                            self._r = list(rows)

                        @property
                        def description(self):
                            return [('a',)]

                        def execute(self, sql):
                            pass

                        def fetchmany(self, size):
                            calls.append(size)
                            out, self._r = self._r[:size], self._r[size:]
                            return out

                        def close(self):
                            pass

                    return Cur()

                def close(self):
                    pass

            return C()

    src = GenericSqlSource('postgres', 'dsn', BatchDriver, connect_timeout=1)
    got = list(src.fetch_rows('_Reference7', batch_size=2))
    assert got == [{'a': i} for i in range(5)]
    assert 2 in calls  # серверный курсор запрошен, fetchmany порциями
    src.close()


# ---- интеграционный тест: реальный PostgreSQL (CI-сервис) ----
@pytest.mark.skipif(not os.environ.get('ONEC_TEST_PG_DSN'),
                    reason='ONEC_TEST_PG_DSN не задан (docker-postgres в CI)')
def test_postgres_integration_reads_v8_tables():
    import psycopg2  # noqa: F401 — интеграционный тест требует драйвер

    from onec_converter.sql_source import build_sql_source

    dsn = os.environ['ONEC_TEST_PG_DSN']
    src = build_sql_source('postgres', dsn)
    # в CI-сервисе заранее созданы служебные таблицы (см. ci.yml seed)
    tables = src.list_tables()
    assert '_Reference1' in tables
    meta = src.fetch_metadata()
    assert any(o.table == '_Reference1' for o in meta)
    rows = list(src.fetch_rows('_Reference1', batch_size=10))
    assert rows  # сид-строка присутствует
    src.close()
