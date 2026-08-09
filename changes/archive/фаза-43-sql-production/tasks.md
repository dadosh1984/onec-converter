# Tasks — Фаза 43: SQL-источники production-grade (0.26.0)

## sql_source
- [x] [fact] _connect(): connect_timeout (не зависать на недоступном сервере)
- [x] [fact] fetch_rows(): потоковая fetchmany; postgres — серверный курсор

## Доки / CI
- [x] [fact] README «SQL-источники: ограничения» (честный контракт)
- [x] [fact] CI: job sql-pg с postgres-сервисом + интеграционный тест

## Тесты/релиз
- [x] [fact] тесты +5 (таймаут, fallback, потоковость, интеграция)
- [x] [assumption] ворота зелёные; релиз 0.26.0
