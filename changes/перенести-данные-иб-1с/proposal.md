# Предложение — перенести-данные-иб-1с

## Цель
Перенести все данные из ИБ 1С 8.1 (E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1, файл 1Cv8.1CD ~2.5 ГБ) на ИБ 1С 8.3 (E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3, файл 1Cv8.1CD ~2 ГБ) через MCP-сервер onec-converter (первый запуск). Источник 8.1 — read-only, работаем только с копией приёмника. Ведём полный пайплайн по плейбуку: base_health → table_sizes → compare_structures → explain_diff → auto_map_schemas → query_sql → migrate (или load_direct в копию 1Cv8.1CD приёмника) → guid_diff → audit_verify → pipeline_status. Фиксируем каждый шаг в result.md. Ошибки оперативно решаем через orion, после исправления обновляем репозиторий onec-converter (commit, push, публикация релиза).

## Контекст

| Аспект | Значение |
|--------|----------|
| Платформа | any |
| Бюджет | compact |
| Ограничения | compact |

- **Lessons applied (v0.12):** скилл-onec-converter-migration:forge:d89d5187918c, скилл-onec-converter-migration:forge:684890ea40c4, скилл-onec-converter-migration:forge:bc925d77a1ff, скилл-onec-converter-migration:forge:56cc53ac3e99, orion-spec:session:eb355cdf0851
