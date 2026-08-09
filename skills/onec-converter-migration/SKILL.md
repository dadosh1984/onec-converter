---
name: onec-converter-migration
description: Выполняет перенос данных между информационными базами 1С (7.7/8.x → 8.x) через MCP-сервер onec-converter. Используй, когда пользователь просит мигрировать/перенести справочники, документы, регистры между базами 1С, изучить структуру базы (1Cv8.1CD/1Cv7.dat), сравнить две конфигурации, выгрузить выборку в Excel/JSON, составить правила маппинга (TOON) или проверить полноту переноса.
license: MIT
metadata:
  version: 0.43.0
---

# Миграция данных 1С через onec-converter (MCP)

Агент работает с MCP-сервером `onec-converter` (18 тулов). Это перенос
**пользовательских данных** между ИБ 1С (справочники, документы, регистры,
перечисления) без платформы 1С. Конфигурация (код, метаданные, права) НЕ
переносится — она готовится штатными средствами.

## Доступные тулы

- **Разведка**: `tools`, `pipeline_status`, `base_health`, `table_sizes`,
  `search_schema`, `query_sql`, `dump_metadata`, `config_versions`
- **Сравнение/маппинг**: `compare_structures`, `guid_diff`, `explain_diff`,
  `auto_map_schemas`, `compress_metadata`, `playbook`
- **Перенос**: `migrate`, `step_init`, `step_inspect_source`,
  `step_inspect_target`, `step_extract`, `step_map`, `step_prevalidate`,
  `step_load` (шаги — в плейбуке)
- **Проверка/безопасность**: `audit_verify`, `load_direct`

## Универсальная последовательность (плейбук)

Весь перенос веди по плейбуку — каждый ответ тула содержит поле `next`
(рекомендуемую следующую команду). Базовый порядок:

1. `table_sizes(source_dir)` — оценить объём (что и сколько переносить).
2. `compare_structures(source_dir, target_dir)` — расхождения структур.
3. `step_init(project_dir, source_ib_id, target_ib_id, source_dir)` —
   зафиксировать пару (правило «1→1»).
4. `step_inspect_source()` → `step_inspect_target()` — метаданные обеих баз.
5. `step_map(meta_source, meta_target, rules)` — валидация/правила TOON
   (или `auto_map_schemas(source_dir, target_dir)` для автогенерации правил).
6. `step_extract(out_file)` — извлечение данных источника.
7. `step_prevalidate()` → preview → `step_load(...)` — запись в приёмник.
8. `verify` / `guid_diff(source_dir, target_dir)` — полнота и целостность.

## Источники и приёмник

- **7.7**: каталог ИБ с `1Cv7.MD` + `1Cv77.dat` (кодировка cp866/cp1251).
- **8.x**: файловая ИБ `1Cv8.1CD`.
- **Приёмник 8.x**: копия 1CD (`load_direct`/`migrate`) или HTTP-сервис.
- Реальные базы изменяются ТОЛЬКО на копиях; оригиналы — read-only.

## Примеры запросов пользователя

- «Изучи базу по пути E:\bases\1C_8.1» → `base_health`/`table_sizes`/`inspect`.
- «Перенеси справочник Номенклатура из 7.7 в 8.3» → разведка → init → extract
  → map → load → verify.
- «Сравни две базы по GUID» → `guid_diff(source_dir, target_dir)`.
- «Выгрузи первые 50 строк таблицы _Reference51 в Excel» →
  CLI `onec-converter export-xlsx` (вне MCP) или `query_sql` → JSON.

## При завершении

После загрузки всегда делай сверку полноты (`verify`/`guid_diff`) и
информируй пользователя о количестве перенесённых объектов, таблиц и об
отчёте.
