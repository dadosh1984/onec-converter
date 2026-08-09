# Spec: core

## Purpose
Позволить извлекать данные из ИБ 1С, размещённой на SQL-сервере
(PostgreSQL / MS SQL), через ту же команду extract. Контракт без жёсткой
привязки к драйверу (ленивый импорт), тестируемость через mock-драйвер.
Версия 0.19.0.

## Acceptance criteria
- [x] sql_source.py: протокол SqlSource (list_tables/fetch_metadata/
      fetch_rows/close) + GenericSqlSource адаптер; build_sql_source
      (ленивый importlib), SqlSourceError с подсказкой при отсутствии
      драйвера/недоступности сервера
- [x] адаптер читает таблицы конфигурации через information_schema
      (_Reference/_Document/_InfoRg/_AccumRg/_Enum префиксы)
- [x] CLI extract: --source-kind 1cd|postgres|mssql, --source-url; при
      SQL-источнике минует _detect_version/1Cv8.1CD
- [x] read_objects возвращает make_object-совместимые объекты
- [x] тесты +5 на mock-драйвере без реальных серверов
- [x] README: SQL-источники + честная spike-граница (детальный парсинг
      v8_metadata ограничен)
- [x] Ворота: pytest (+5), conformance, ruff, mypy (46), check_bsl,
      vitest — зелёные; релиз 0.19.0
