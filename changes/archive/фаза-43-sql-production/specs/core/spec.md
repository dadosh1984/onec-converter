# Spec: core

## Purpose
Довести SQL-источники до production-grade: таймаут подключения, потоковая
выборка без загрузки в память, честная документация ограничений и
интеграционный тест на реальном PostgreSQL в CI. Версия 0.26.0.

## Acceptance criteria
- [x] _connect(): connect_timeout (по умолчанию 10 с; postgres ->
      connect_timeout kwarg, mssql -> timeout kwarg); fallback на
      драйверы/моки без kwarg (TypeError); недоступный сервер -> SqlSourceError
- [x] fetch_rows(table, batch_size=1000): генератор через fetchmany
      порциями; postgres — именованный серверный курсор (psycopg2),
      fallback на обычный; идентификатор валидируется/кавычится (Фаза 41)
- [x] README: раздел «SQL-источники: ограничения» — честный контракт
      (имена=таблицы, v8_metadata не парсится, типы пустые; файловый
      источник для production)
- [x] CI: job sql-pg (postgres:16 сервис, сид _Reference1,
      ONEC_TEST_PG_DSN) — интеграционный тест на реальной СУБД;
      локально skip без env
- [x] Тесты: таймаут (kwarg/fallback/ошибка), потоковость (fetchmany
      порциями, 2 в calls), интеграция PG (env-gated)
- [x] Ворота: pytest (+5, 1 локальный skip), conformance, ruff,
      mypy (52), check_bsl, vitest — зелёные; релиз 0.26.0
