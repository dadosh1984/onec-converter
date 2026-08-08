"""Тесты SQL-коннектора (интерфейс)."""
import pytest

from onec_converter.source_sql import SqlSource, SqlSourceError


def test_sql_source_not_configured():
    with pytest.raises(SqlSourceError):
        SqlSource('dsn').tables()
