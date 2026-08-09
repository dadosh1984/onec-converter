# Tasks — Фаза 41: хирургические дефекты раунда 4 (0.24.0)

## openapi
- [x] [fact] gen_openapi: версия из onec_converter.__version__
- [x] [fact] gen_openapi: BearerAuth для /metadata и /load

## audit
- [x] [fact] _rotate(): маркер-запись {"marker":"rotated","prev_hash":...}
- [x] [fact] verify_audit(): валидация prev_hash первой записи

## sql_source
- [x] [fact] fetch_rows: валидация/кавычки имени таблицы (anti-injection)
- [x] [fact] MSSQL col_sql: скобки AND+OR, ESCAPE

## Тесты/доки/релиз
- [x] [fact] тесты +7 (openapi version, golden-ротация, первая запись, инъекция)
- [x] [assumption] ворота зелёные; релиз 0.24.0
