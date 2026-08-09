# Задачи — скилл-onec-converter-migration

Легенда статусов: отмеченный квадрат означает готово, пустой —
открыто; forge переключает каждый квадрат по мере выполнения задачи,
так что ручная сверка не нужна.

## RED — воспроизвести поломку

- [x] [assumption] Тест RED tests/test_mcp_tool_surface.py: для каждого имени тула из PLAYBOOK и из docs/playbook.md (и SKILL.md) — имя есть в реестре visible_tool / tools/list. На текущем коде падает: step_init/step_extract/step_map/step_load/verify/transform/preview/inspect отсутствуют.

## GREEN — реализация

- [x] [fact] Исправить src/onec_converter/mcp_server.py: константа PLAYBOOK и playbook() ссылаются только на реальные 18 тулов; поле next каждого тула и пример не содержат step_*/verify/transform/preview/inspect.
- [x] [fact] Переписать docs/playbook.md: «Универсальная последовательность» — только реальные тулы; пример «зарплаты 8.1→8.3» через migrate()/выборочную проверку; убрать 16-шаговый step-пайплайн, заменить на описания реальных команд.
- [x] [fact] Переписать скилл skills/onec-converter-migration/SKILL.md: секция «Доступные тулы» и «Универсальная последовательность» — только 18 реальных тулов; корректный порядок (разведка → маппинг → migrate/load_direct → сверка); убрать шаги, которых нет в реестре.
- [x] [fact] Синхронизировать глобальную копию ~/.pi/agent/skills/onec-converter-migration/SKILL.md с исправленной проектной (diff идентичен).

## GREEN — проверка

- [x] [assumption] Полный прогон тестов и ворот не сломан: pytest 557 / ruff src+tests / mypy src+scripts / vitest 355; E2E stdio: tools/list возвращает 18 тулов, `next`/playbook ссылаются только на реальные.
