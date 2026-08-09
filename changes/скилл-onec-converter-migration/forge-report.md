# Forge Report — скилл-onec-converter-migration

- **Status:** paused
- **Done:** 0 · **Skipped (cache):** 0 · **Pending:** 6
- **Generated:** 2026-08-09T09:16:32.721Z

| Task | Status |
|------|--------|
| [assumption] Тест RED tests/test_mcp_tool_surface.py: для каждого имени тула из PLAYBOOK и из docs/playbook.md (и SKILL.md) — имя есть в реестре visible_tool / tools/list. На текущем коде падает: step_init/step_extract/step_map/step_load/verify/transform/preview/inspect отсутствуют. | pending |
| [fact] Исправить src/onec_converter/mcp_server.py: константа PLAYBOOK и playbook() ссылаются только на реальные 18 тулов (migrate, load_direct, query_sql, guid_diff, auto_map_schemas, compare_structures, search_schema, table_sizes, compress_metadata, dump_metadata, config_versions, audit_verify, cache_stats, base_health, pipeline_status, explain_diff, playbook, tools); поле next каждого тула и пример не содержат step_*/verify/transform/preview/inspect. | pending |
| [fact] Переписать docs/playbook.md: «Универсальная последовательность» — только реальные тулы; пример «зарплаты 8.1→8.3» через migrate()/выборочную проверку; убрать 16-шаговый step-пайплайн, заменить на описания реальных команд. | pending |
| [fact] Переписать скилл skills/onec-converter-migration/SKILL.md: секция «Доступные тулы» и «Универсальная последовательность» — только 18 реальных тулов; корректный порядок (разведка → маппинг → migrate/load_direct → сверка); убрать шаги, которых нет в реестре. | pending |
| [fact] Синхронизировать глобальную копию ~/.pi/agent/skills/onec-converter-migration/SKILL.md с исправленной проектной (diff идентичен). | pending |
| [assumption] Полный прогон тестов и ворот не сломан: pytest (с ONEC_TEST_TMP), ruff, mypy, vitest; тест-обработ видит, что каждый тул из SKILL.md/playbook/docs существует в tools/list сервера (E2E stdio). | pending |

Waiting for implementation snippets:
- `changes/скилл-onec-converter-migration/snippets/тест_red_tests.ts`
- `changes/скилл-onec-converter-migration/snippets/исправить_src_onec.ts`
- `changes/скилл-onec-converter-migration/snippets/переписать_docs_playbook.ts`
- `changes/скилл-onec-converter-migration/snippets/переписать_скилл_skills.ts`
- `changes/скилл-onec-converter-migration/snippets/синхронизировать_глобальную_копию.ts`
- `changes/скилл-onec-converter-migration/snippets/полный_прогон_тестов.ts`
