# Карта команд onec-converter (Фаза 29.1)

Сгенерировано из фактического реестра: CLI 38 подкоманд, MCP 18 тулов.
Поток данных: inspect → extract → map → transform → load → verify.

## CLI (38)

| Команда | Вход | Выход | Назначение |
|---|---|---|---|
| inspect | source_dir | метаданные | структура источника (7.7/8.x) |
| extract | source_dir | batch.json | объекты в промежуточный формат |
| map | source_dir, target_dir | rules.json | генерация правил TOON |
| transform | input, rules_file | out.json | применение правил |
| load | input (+direct/http) | приёмник | загрузка (файл/HTTP/прямая запись) |
| status | — | пайплайн | состояние шагов/кеша |
| query | source_dir, sql | выборка | SQL-подобный запрос к таблицам |
| guid-diff | source_dir, target_dir | diff | сверка GUID двух баз |
| config-versions | source_dir | версии | версии конфигурации/платформы |
| doctor | — | отчёт | самодиагностика окружения |
| cache | — | кеш | инвалидация/просмотр кеша метаданных |
| dump-records | source_dir | файл | выгрузка записей таблицы |
| metrics | — | Prometheus | метрики |
| clone-db | source_dir, target_dir | копия | полная копия ИБ (стенд) |
| audit | audit.jsonl | отчёт | просмотр/фильтр журнала |
| techlog | source_dir | события | техжурнал 1С как источник |
| fetch-config | source | метаданные | релиз конфигурации (XML-выгрузка; рус. и англ. теги MDClasses) |
| dump-report | file, s3 | S3 | экспорт отчёта в S3 (SigV4) |
| sonar-report | target | XML/JSON | отчёт ruff в sonar-формате |
| export-kd3 | rules.json | XML | правила TOON в XML КД3-стиля |
| mint-token | secret | JWT | выпуск локального HS256 Bearer-токена (Фаза 33) |
| pii-report | audit.jsonl | JSON | отчёт по анонимизации ПДн (152-ФЗ/152 УЗ, Фаза 37) |
| stats | source_dir | сводка | таблицы/строки/объём/locale |
| mcp | — | тулы | список MCP-тулов сервера |
| export-xlsx | source_dir, table | xlsx | экспорт N строк таблицы в Excel |
| xlsx-export | source_dir, table | xlsx | выгрузка записей объекта в XLSX-мост (U27) |
| xlsx-to-intermediate | xlsx, type | JSON | конвертация XLSX-шаблона приёмника в intermediate (U27) |
| bridge-export | source_dir, type | xlsx | справочник/регистр -> xlsx-мост (аналог epf-макета) |
| bridge-import | xlsx, target_dir | копия | xlsx-мост -> копия приёмника (find-or-create) |
| bridge-verify | xlsx, target_dir(копия) | отчёт | обратный контроль: сверка данных копии приёмника с мостом |
| shell | source-dir | REPL | интерактивное исследование базы (tables/query, Фаза 39) |
| migrate | source-dir, out | JSON/direct | сквозной перенос одной командой: extract→transform→load (Фаза 56) |
| wizard | (интерактив) | команда | мастер переноса, собирает и запускает migrate (Фаза 56) |
| audit-verify | audit.jsonl | rc | проверка tamper-evident цепочки (+ --cross-files, Фаза 42) |
| ai-map | source+target dir | rules | авто-маппинг схем -> правила TOON (Фаза 45) |
| ai-explain | source+target dir | текст | причины расхождений структур (Фаза 45) |
| verify | --input --target | rc/json | сверка источник↔приёмник, отчёт для CI (Фаза 48) || rules-diff | --a --b | rc | сравнение двух правил TOON (Фаза 48) |

Общие флаги: `--source-dir`, `--out`, `--format json|xlsx`, `--audit-file`.

## MCP (18 тулов)

`tools` (плейбук) → pipeline_status → inspect/extract/map/transform/load
(виртуальные шаги плейбука через tools()); реальные тулы:

audit_verify, auto_map_schemas, base_health, cache_stats, compare_structures,
compress_metadata, config_versions, dump_metadata, explain_diff, guid_diff,
load_direct, migrate, pipeline_status, playbook, query_sql, search_schema,
table_sizes, tools.


| Тул | Вход | Выход | next |
|---|---|---|---|
| tools | — | плейбук (10 шагов) | первый шаг |
| pipeline_status | — | состояние пайплайна | следующий шаг |
| search_schema | source_dir, query | метаданные/поля | — |
| table_sizes | source_dir, format | размеры (json/xlsx) | — |
| compare_structures | source_dir, target_dir | diff (json/xlsx) | — |
| base_health | source_dir | здоровье базы | — |
| query_sql | source_dir, sql | выборка | — |
| guid_diff | source_dir, target_dir | сверка GUID | — |
| config_versions | source_dir | версии | — |
| dump_metadata | source_dir | дамп метаданных | — |
| load_direct | target_dir, objects | копия 1CD | verify |
| playbook | — | последовательность команд | — |
| migrate | source_dir, target_dir, rules | сквозной перенос | verify |
| auto_map_schemas | source_dir, target_dir | авто-маппинг | — |
| explain_diff | source_dir, target_dir | причины расхождений | — |
| compress_metadata | source_dir, top_tables | саммари для LLM | — |
| audit_verify | audit_file, cross_files | целостность журнала | — |
| cache_stats | root_dir | метрики кеша | — |

## Взаимосвязи (проверка Фазы 29.1)

- Реестр CLI: каждая подкоманда имеет обработчик (20/20), мёртвых нет —
  все вызываются в пайплайне или сервисные (doctor/cache/metrics/audit).
- Аргументы согласованы: `--source-dir`/`--out`/`--format` одинаковы
  в extract/transform/table_sizes/compare_structures.
- MCP: 18 реальных тулов; дубли удалены в Фазе 29.1
  (дубли объединены через --format, см. CHANGELOG 0.7.0);
  compress_metadata/audit_verify/cache_stats добавлены в Фазе 51 (0.34.0);
  next-цепочки ведут по плейбуку (см. docs/playbook.md).
