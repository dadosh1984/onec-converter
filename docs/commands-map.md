# Карта команд onec-converter (Фаза 29.1)

Сгенерировано из фактического реестра: CLI 22 подкоманды, MCP 13 тулов.
Поток данных: inspect → extract → map → transform → load → verify.

## CLI (22)

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
| fetch-config | source | метаданные | релиз конфигурации (XML-выгрузка) |
| dump-report | file, s3 | S3 | экспорт отчёта в S3 (SigV4) |
| sonar-report | target | XML/JSON | отчёт ruff в sonar-формате |
| export-kd3 | rules.json | XML | правила TOON в XML КД3-стиля |
| mint-token | secret | JWT | выпуск локального HS256 Bearer-токена (Фаза 33) |
| pii-report | audit.jsonl | JSON | отчёт по анонимизации ПДн (152-ФЗ/152 УЗ, Фаза 37) |

Общие флаги: `--source-dir`, `--out`, `--format json|xlsx`, `--audit-file`.

## MCP (13 тулов)

`tools` (плейбук) → pipeline_status → inspect/extract/map/transform/load
(виртуальные шаги плейбука через tools()); реальные тулы:

base_health, compare_structures, config_versions, dump_metadata, guid_diff,
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

## Взаимосвязи (проверка Фазы 29.1)

- Реестр CLI: каждая подкоманда имеет обработчик (20/20), мёртвых нет —
  все вызываются в пайплайне или сервисные (doctor/cache/metrics/audit).
- Аргументы согласованы: `--source-dir`/`--out`/`--format` одинаковы
  в extract/transform/table_sizes/compare_structures.
- MCP: 13 реальных тулов; дубли удалены в Фазе 29.1
  (дубли объединены через --format, см. CHANGELOG 0.7.0);
  next-цепочки ведут по плейбуку (см. docs/playbook.md).
