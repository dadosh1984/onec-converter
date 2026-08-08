// GREEN: source_sql — чтение серверных ИБ (MS SQL / PostgreSQL) через SQL
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_source_sql_ms_sql_postgresql_sql_unit_in_memory() {
  const files: Record<string, string> = {
    'src/onec_converter/source_sql.py': `"""Чтение серверных ИБ 1С 8.x (MS SQL / PostgreSQL) — опциональный коннектор.

Серверные ИБ хранят те же таблицы (_ReferenceNN, _DocumentNN, ...) в СУБД.
Коннектор: подключение (SQLAlchemy/psycopg2/pyodbc — выбор при реализации),
список таблиц (information_schema), чтение строк, маппинг имён через DBSCHEMA.
Требуются доступы к СУБД; интерфейс единый с source_8x_file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator


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
`,
    'tests/test_source_sql.py': `"""Тесты SQL-коннектора (интерфейс)."""
import pytest

from onec_converter.source_sql import SqlSource, SqlSourceError


def test_sql_source_not_configured():
    with pytest.raises(SqlSourceError):
        SqlSource('dsn').tables()
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
