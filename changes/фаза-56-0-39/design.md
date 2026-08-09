# Дизайн — Фаза 56 (0.39.0): функциональность

По аудиту раунда 6 (docs/audit-round-6d.md), раздел C + G2.

## Сделано
- C1: `onec-converter mcp --stdio/--sse` — запуск MCP-сервера из CLI.
  Добавлен `mcp_server.server_main(transport)` как реальная точка входа;
  раньше `python -m onec_converter.mcp_server` лишь импортировал модуль
  и завершался (README обещал сервер — стало честно рабочим).
- C4: CLI `migrate` — сквозной перенос одной командой (extract → transform
  по правилам TOON → load в файл или --direct в копию 1CD). Источники 7.7/8.x.
- G2: CLI `wizard` — интерактивный мастер: вопросы → сбор и запуск команды
  migrate; `--no-run` печатает команду без выполнения (безопасно для CI).

## Совместимость / тесты
- Команды CLI 31 -> 33; обновлены contract-тесты (test_phase29/48: 33) и
  docs/commands-map.md (CLI (33) + строки migrate/wizard).
- `mcp` (список тулов) без --stdio не изменился — 18 тулов.

## Верификация
- ruff/mypy/gates green; pytest 534 (+6 Фаза 56); vitest 355;
  openapi 0.39.0.
