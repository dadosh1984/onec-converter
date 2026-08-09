# Spec: core

## Назначение
Перенести все данные из ИБ 1С 8.1 (E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1, файл 1Cv8.1CD ~2.5 ГБ) на ИБ 1С 8.3 (E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3, файл 1Cv8.1CD ~2 ГБ) через MCP-сервер onec-converter (первый запуск). Источник 8.1 — read-only, работаем только с копией приёмника. Ведём полный пайплайн по плейбуку: base_health → table_sizes → compare_structures → explain_diff → auto_map_schemas → query_sql → migrate (или load_direct в копию 1Cv8.1CD приёмника) → guid_diff → audit_verify → pipeline_status. Фиксируем каждый шаг в result.md. Ошибки оперативно решаем через orion, после исправления обновляем репозиторий onec-converter (commit, push, публикация релиза).

## Область

- В области: указанная возможность, поставляется тест-первой.
- Вне области: всё, что не заявлено в предложении.

## Критерии приёмки
- [ ] Заполнить в ходе реализации
