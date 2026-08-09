# Spec: core

## Назначение
Исправить скилл onec-converter-migration (и связанные плейбук-доки), которые ссылаются на несуществующие MCP-тулы (step_init, step_extract, step_map, step_load, verify, transform, preview), из-за чего агент по скиллу вызывает несуществующие тулы и получает "Unknown tool" — скилл не работает. Реальный сервер onec-converter v0.43.1 отдаёт только 18 MCP-тулов; шаги пайплайна (init→inspect→extract→map→transform→validate→load) выполняются внутри ЕДИНОГО тула `migrate()`. Нужно: 1) переписать ~/.pi/agent/skills/onec-converter-migration/SKILL.md и проектную копию skills/onec-converter-migration/SKILL.md на реальный API 18 тулов (migrate, load_direct, query_sql, guid_diff, auto_map_schemas, compare_structures, search_schema, table_sizes, compress_metadata, dump_metadata, config_versions, audit_verify, cache_stats, base_health, pipeline_status, explain_diff, playbook, tools) с корректной последовательностью; 2) исправить константу PLAYBOOK и playbook() в src/onec_converter/mcp_server.py и docs/playbook.md, чтобы поле next и примеры ссылались только на реальные тулы; 3) добавить тест, что каждый тул/имя из SKILL.md и playbook'а есть в реестре visible_tool (актуально против 'Unknown tool').

## Область

- В области: указанная возможность, поставляется тест-первой.
- Вне области: всё, что не заявлено в предложении.

## Критерии приёмки
- [ ] Заполнить в ходе реализации
