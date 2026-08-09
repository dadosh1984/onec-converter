# Tasks — Фаза 36: SQL-источники (0.19.0)

## Абстракция
- [x] [fact] sql_source.py: SqlSource (list_tables/fetch_metadata/fetch_rows),
      GenericSqlSource, build_sql_source, SqlSourceError
- [x] [fact] adapters: ленивый importlib psycopg2/pyodbc, information_schema
      таблицы объектов

## CLI
- [x] [fact] extract --source-kind 1cd|postgres|mssql + --source-url
- [x] [fact] README — SQL-источники + spike-граница

## Тесты / релиз
- [x] [fact] тесты +5 на mock-драйвере (без реальных серверов)
- [x] [fact] CHANGELOG 0.19.0; план Фаза 36 ✅
- [x] [assumption] ворота зелёные; релиз 0.19.0
