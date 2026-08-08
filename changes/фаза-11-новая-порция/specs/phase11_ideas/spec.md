# Spec: phase11_ideas

## Purpose

Фаза 11: пересмотр блок-листа идей (docs/ideas.md) и реализация трёх идей
авторским кодом (только stdlib, реальные базы read-only): консоль запросов
конфигурации (SQL-подобный язык), сравнение ИБ по GUID, версии конфигурации
(формат/ИБ/платформа + дифф CONFIG↔CONFIGSAVE).

## Capabilities

### query_table_sql (query.py)

- Безопасная SQL-подобная выборка записей таблицы 1CD: SELECT (проекция
  полей или `*`), WHERE (`=`, `!=`, `<`, `>`, `<=`, `>=`, `LIKE`),
  ORDER BY (`field ASC|DESC`), LIMIT.
- REF-поля → `{"guid","name"}` через `ref_name()`.
- Синтаксис WHERE совместим с существующим тулом `query_table` (C3).

### guid_diff (guid_diff.py)

- Сверка двух баз по GUID: объекты конфигурации (read_metadata) и таблицы
  (read_dbnames) — только-в-источнике / только-в-приёмнике / общие
  с расхождениями имени/типа. Проверка полноты переноса на уровне ссылок.

### config_versions (config_versions.py)

- Версии из файла базы: формат (db.version), версия ИБ и требуемая версия
  платформы (IBVERSION), статистика файлов CONFIG/CONFIGSAVE/PARAMS (число,
  даты), дифф CONFIG↔CONFIGSAVE (добавлено/удалено/изменено по размеру) —
  «что изменилось с последнего сохранения».

## Acceptance criteria

- [ ] query: выборка с проекцией/фильтрами/сортировкой/лимитом на fake_1cd
      и реальной базе (R-поля); CLI и MCP-тул работают
- [ ] guid_diff: отчёт по GUID двух баз (синтетика + реальные); CLI и MCP
- [ ] config_versions: формат/ИБ/платформа + дифф CONFIG↔CONFIGSAVE
      (fake_1cd + реальная база); CLI и MCP
- [ ] docs/ideas.md (трек E + пересмотр «Не взято»), docs/format-8x.md
      («Версии и сохранения»), README («Фаза 11» со статусами)
- [ ] Ворота: pytest (вкл. integration) / mypy strict / ruff / vitest
