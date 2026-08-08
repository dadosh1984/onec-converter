# Tasks — фаза-11-новая-порция

Пересмотр блок-листа идей (docs/ideas.md) + реализация 3 идей: консоль запросов
конфигурации (SQL-подобный язык), сравнение ИБ по GUID, версии конфигурации
(формат/ИБ/платформа + дифф CONFIG↔CONFIGSAVE). Только stdlib.

- [x] [spike] Пересмотр блок-листа + формат: PARAMS/IBVERSION/CONFIG/CONFIGSAVE/
      `versions`/`version` (что лежит, как читать: версии, даты, имена файлов
      конфигурации) → раздел «Версии и сохранения» в docs/format-8x.md;
      docs/ideas.md — трек E (E1–E3) + обновление «Не взято» (история версий
      хранилища отсутствует в файле базы; CONFIGSAVE = последнее сохранение)
- [x] [fact] `query.py`: `query_table_sql(db, table, select, where, order_by,
      limit)` — безопасный мини-SQL (SELECT/WHERE/ORDER BY/LIMIT, LIKE), REF →
      {guid,name}; unit-тесты на fake_1cd + реальной базе (R-поля, integration)
- [x] [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты
- [x] [fact] `guid_diff.py`: `guid_diff(source_dir, target_dir)` — объекты и
      таблицы двух баз по GUID (read_metadata + read_dbnames): только-в-источнике /
      только-в-приёмнике / общие с расхождениями; unit-тесты (синтетика + integration)
- [x] [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты
- [x] [fact] `config_versions.py`: `config_versions(path)` — формат, версия ИБ/
      платформы (IBVERSION), статистика CONFIG/CONFIGSAVE/PARAMS, дифф
      CONFIG↔CONFIGSAVE (добавлено/удалено/изменено); unit-тесты (fake_1cd +
      integration)
- [x] [assumption] CLI `onec-converter config-versions` + MCP-тул `config_versions`;
      unit-тесты
- [x] [assumption] README: раздел «Фаза 11» со статусами (E1–E3 + пересмотр
      блок-листа)

Ворота: pytest (вкл. integration), mypy strict, ruff, vitest (Orion shield).
Python 3.11+, Windows, реальные базы read-only. Только stdlib.
