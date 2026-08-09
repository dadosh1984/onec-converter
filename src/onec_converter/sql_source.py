"""SQL-источники 1С (PostgreSQL / MS SQL), Фаза 36.

Чтение ИБ 1С, размещённой не в файле 1Cv8.1CD, а на SQL-сервере. Внимание:
точный парсинг служебных таблиц 1С (v8_metadata, _Reference…, _InfoRg,
_AccumRg) — большая отдельная работа. Здесь реализован честный контракт:
адаптер возвращает метаданные (объекты конфигурации) и строки таблиц в том
же виде, что read_table (name->значение), чтобы extract/load не зависели от
источника. Реальные подключения к серверу — через драйвер, импортируется
лениво (psycopg2 для PostgreSQL, pyodbc для MSSQL); без драйвера поднимается
ошибка с понятной подсказкой.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from .intermediate import OBJ_ATTRS, OBJ_ID, OBJ_KEY, OBJ_REFS, OBJ_TYPE


class SqlSourceError(Exception):
    """Ошибка чтения SQL-источника."""


@dataclass
class SqlObject:
    """Метаданные объекта конфигурации в SQL-ИБ."""
    kind: str          # Справочник/Документ/РегистрСведений/...
    name: str
    table: str         # физическое имя таблицы (_Reference7 / _InfoRg10)
    columns: dict[str, str]  # реквизит -> тип (для object_to_row)


class SqlSource(Protocol):
    """Контракт источника SQL-ИБ (PostgreSQL/MSSQL)."""

    def list_tables(self) -> list[str]: ...
    def fetch_metadata(self) -> list[SqlObject]: ...
    def fetch_rows(self, table: str) -> Iterable[dict[str, Any]]: ...
    def close(self) -> None: ...


def _driver_for(kind: str) -> object:
    """Ленивый импорт драйвера; SqlSourceError при недоступности."""
    import importlib

    try:
        if kind == 'postgres':
            return importlib.import_module('psycopg2')
        if kind == 'mssql':
            return importlib.import_module('pyodbc')
    except ImportError as exc:
        raise SqlSourceError(
            f'драйвер для {kind} не установлен: {exc}. '
            f'Установите psycopg2 (PostgreSQL) или pyodbc (MS SQL).'
        ) from exc
    raise SqlSourceError(f'неизвестный SQL-источник: {kind}')


def build_sql_source(kind: str, dsn: str,
                      driver: Any | None = None) -> GenericSqlSource:
    """Создать адаптер по типу источника и DSN (без подключения).

    driver — для тестов и кастомных DRIVER; по умолчанию лениво
    импортируется psycopg2 (postgres) / pyodbc (mssql).
    """
    if driver is None:
        driver = _driver_for(kind)
    return GenericSqlSource(kind, dsn, driver)


class GenericSqlSource:
    """Адаптер поверх драйвера: высокоуровневое чтение v8_* таблиц.

    Реальный парсинг палитры 1С (код таблиц, ссылки) ограничен базовой
    эвристикой: имена таблиц-объектов извлекаются по префиксам _Reference/
    _Document/_InfoRg/_AccumRg + номер, метаданные колонок — по системному
    каталогу (information_schema / dbo). Уточнение структуры — на стороне
    SQL-прослойки приёмника. (Честная [spike]-граница.)
    """

    _KIND_PREFIX: ClassVar[dict[str, str]] = {
        'Справочник': '_Reference',
        'Документ': '_Document',
        'РегистрСведений': '_InfoRg',
        'РегистрНакопления': '_AccumRg',
        'Перечисление': '_Enum',
    }

    def __init__(self, kind: str, dsn: str, driver: Any) -> None:
        self.kind = kind
        self.dsn = dsn
        self._driver = driver
        self._conn: Any = None

    def _connect(self) -> Any:
        if self._conn is None:
            exc = None
            for _ in range(2):
                try:
                    if self.kind == 'postgres':
                        self._conn = self._driver.connect(self.dsn)
                    else:
                        self._conn = self._driver.connect(self.dsn)
                    break
                except Exception as e:  # noqa: BLE001 — retry-обёртка
                    exc = e
            if self._conn is None:
                raise SqlSourceError(f'не удалось подключиться к {self.kind}: {exc}')
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def _q(self, sql: str) -> list[dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(sql)
            cols = [d[0] for d in cur.description or []]
            rows = cur.fetchall()
        finally:
            cur.close()
        out = []
        for r in rows:
            out.append(dict(zip(cols, r)))
        return out

    def list_tables(self) -> list[str]:
        """Таблицы, относящиеся к объектам конфигурации (по префиксам)."""
        schema = 'public' if self.kind == 'postgres' else 'dbo'
        sql = (f"SELECT table_name FROM information_schema.tables "
               f"WHERE table_schema = '{schema}' AND ("
               f"table_name LIKE '\\_Reference%' ESCAPE '\\\\' OR "
               f"table_name LIKE '\\_Document%' ESCAPE '\\\\' OR "
               f"table_name LIKE '\\_InfoRg%' ESCAPE '\\\\' OR "
               f"table_name LIKE '\\_AccumRg%' ESCAPE '\\\\' OR "
               f"table_name LIKE '\\_Enum%' ESCAPE '\\\\') "
               f"ORDER BY table_name")
        rows = self._q(sql)
        return [str(r['table_name']) for r in rows]

    def fetch_metadata(self) -> list[SqlObject]:
        """Объекты: kind по префиксу, имя = имя таблицы (справочники без
        имени_CONF — берётся как DBNames-имя). Полноценная схема — TODO."""
        objs: list[SqlObject] = []
        rev = {v: k for k, v in self._KIND_PREFIX.items()}
        for t in self.list_tables():
            kind = next((rev[p] for p in rev if t.startswith(p)), None)
            if kind is None:
                continue
            # имя в SQL-ИБ часто хранится в виде "DBNames": имя может быть
            # нечитаемым без v8_metadata; используем читаемое имя таблицы
            col_sql = {
                'postgres': ("SELECT column_name FROM information_schema.columns "
                             "WHERE table_schema='public' AND table_name=%s"),
                'mssql': ("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                          "WHERE TABLE_NAME=? AND COLUMN_NAME LIKE '\\_Fld%' OR "
                          "COLUMN_NAME='_IDRREF'"),
            }[self.kind]
            conn = self._connect()
            cur = conn.cursor()
            try:
                cur.execute(col_sql, (t,))
                cols = [str(r[0]) for r in cur.fetchall()]
            finally:
                cur.close()
            objs.append(SqlObject(kind=kind, name=t, table=t,
                                  columns={c: '' for c in cols}))
        return objs

    def fetch_rows(self, table: str) -> Iterable[dict[str, Any]]:
        return self._q(f"SELECT * FROM {table}")

    # ---- intermediate-совместимый чтение строк ----
    def read_objects(self) -> Iterable[dict[str, Any]]:
        """Объекты в формате make_object (для extract с --source-kind)."""
        for o in self.fetch_metadata():
            for i, row in enumerate(self.fetch_rows(o.table)):
                yield {
                    OBJ_TYPE: f'{o.kind}.{o.name}',
                    OBJ_ID: str(i),
                    OBJ_KEY: [],
                    OBJ_ATTRS: row,
                    OBJ_REFS: {},
                }
