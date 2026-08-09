---
name: onec-converter-migration
description: Выполняет перенос данных между информационными базами 1С (7.7/8.x → 8.x) через MCP-сервер onec-converter. Используй, когда пользователь просит мигрировать/перенести справочники, документы, регистры между базами 1С, изучить структуру базы (1Cv8.1CD/1Cv7.dat), сравнить две конфигурации, выгрузить выборку в Excel/JSON, составить правила маппинга (TOON) или проверить полноту переноса.
license: MIT
metadata:
  version: 0.43.2
---

# Миграция данных 1С через onec-converter (MCP)

Агент работает с MCP-сервером `onec-converter` (18 тулов). Это перенос
**пользовательских данных** между ИБ 1С (справочники, документы, регистры,
перечисления) без платформы 1С. Конфигурация (код, метаданные, права) НЕ
переносится — она готовится штатными средствами.

Весь полный пайплайн переноса (init → inspect → extract → map → transform →
prevalidate → load) выполняется **одним тулом `migrate()`**; отдельными
`step_*`-тулами он не выставляется. Для прямой записи без HTTP есть
`load_direct` в **КОПИЮ** `1Cv8.1CD` приёмника.

## Доступные тулы (все 18 — реальные)

- **Разведка**: `tools`, `pipeline_status`, `base_health`, `table_sizes`,
  `search_schema`, `query_sql`, `config_versions`, `compress_metadata`,
  `cache_stats`
- **Сравнение/маппинг**: `compare_structures`, `explain_diff`,
  `auto_map_schemas`, `dump_metadata`
- **Перенос**: `migrate` (сквозной: init→inspect→extract→map→transform→
  prevalidate→load), `load_direct` (в копию 1CD), `playbook`
- **Проверка/безопасность**: `guid_diff` (сверка полноты), `audit_verify`
  (целостность журнала)

## Универсальная последовательность (плейбук)

Весь перенос веди по плейбуку — каждый ответ тула содержит поле `next`
(рекомендуемую следующую команду), `playbook()` даёт полный перечень
реальных команд. Базовый порядок на реальных тулах:

1. `table_sizes(source_dir)` / `base_health(source_dir)` — оценить объём
   (что и сколько переносить).
2. `compare_structures(source_dir, target_dir)` → `explain_diff(...)`
   — расхождения структур.
3. `search_schema(source_dir, '<имя>')` — найти объекты/таблицы по имени.
4. `auto_map_schemas(source_dir, target_dir)` — автогенерация TOON-правил
   (поле→поле) по именам/синонимам.
5. `query_sql(source_dir, table, where, limit)` — выборочная проверка записи.
6. `migrate(project_dir, source_ib_id, target_ib_id, source_dir, target_url,
   rules=..., out_file=..., source_encoding='cp866')` — **СКВОЗНОЙ перенос**
   одной командой (внутри: init→inspect→extract→map→transform→prevalidate→load).
   Либо без HTTP: `load_direct(target_dir, input_file, workdir)` в КОПИЮ
   приёмника `1Cv8.1CD`.
7. `guid_diff(source_dir, target_dir)` — сверка полноты по GUID (объекты,
   таблицы).
8. `audit_verify(audit_file)` — целостность журнала миграции.
9. `pipeline_status()` — итог: метрики, кеш, последний шаг.

## Источники и приёмник

- **7.7**: каталог ИБ с `1Cv7.MD` + `1Cv77.dat` (кодировка cp866/cp1251).
- **8.x**: файловая ИБ `1Cv8.1CD`.
- **Приёмник 8.x**: копия 1CD (`load_direct`/`migrate`) или HTTP-сервис.
- Реальные базы изменяются ТОЛЬКО на копиях; оригиналы — read-only.

## Примеры запросов пользователя

- «Изучи базу по пути E:\bases\1C_8.1» → `base_health`/`table_sizes`/`search_schema`.
- «Перенеси справочник Номенклатура из 7.7 в 8.3» → разведка →
  `auto_map_schemas` → `migrate(...)` → `guid_diff` → отчёт.
- «Сравни две базы по GUID» → `guid_diff(source_dir, target_dir)`.
- «Выгрузи первые 50 строк таблицы _Reference51 в Excel» →
  CLI `onec-converter export-xlsx` (вне MCP) или `query_sql` → JSON.

## При завершении

После загрузки всегда делай сверку полноты (`guid_diff`) и информируй
пользователя о количестве перенесённых объектов, таблиц и об отчёте.
