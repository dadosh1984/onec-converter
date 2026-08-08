"""Чтение серверных ИБ 1С 8.x (MS SQL / PostgreSQL) — опциональный коннектор.

Серверные ИБ хранят те же таблицы (_ReferenceNN, _DocumentNN, ...) в СУБД.
Коннектор: подключение (SQLAlchemy/psycopg2/pyodbc — выбор при реализации),
список таблиц (information_schema), чтение строк, маппинг имён через DBSCHEMA.
Требуются доступы к СУБД; интерфейс единый с source_8x_file.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


class SqlSourceError(Exception):
    """Ошибка SQL-коннектора."""


@dataclass
class SqlSource:
    """Чтение таблиц серверной ИБ (интерфейс)."""

    dsn: str

    def tables(self) -> list[str]:
        raise SqlSourceError('SQL-коннектор не подключён: укажите реализацию '
                             '(pyodbc/psycopg) в настройках')

    def rows(self, table: str) -> Iterator[tuple[Any, ...]]:
        raise SqlSourceError('SQL-коннектор не подключён')

    def close(self) -> None:
        pass
