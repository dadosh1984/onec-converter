# Tasks — Фаза 23: Conformance-тесты MCP + CI-гейты

Ворота: mypy strict, ruff, pytest, vitest. Релиз 0.8.0.

## Conformance-набор (E2E stdio)
- [x] [fact] tests/test_mcp_conformance.py: initialize-рукопожатие
      (protocolVersion, serverInfo.name)
- [x] [fact] tools/list: ключевые тулы, дубли 29.1 отсутствуют
- [x] [fact] tools/call: tools() — JSON-блоки, первый 'init'
- [x] [fact] неизвестный тул → isError=true, сервер жив после ошибки
- [x] [fact] pipeline_status: ответ содержит непустое `next`

## Ворота и CI
- [x] [fact] gates.sh: цель `conformance` (5 проверок)
- [x] [fact] gates.sh: флаг `--coverage` — pytest-cov на 5 новых модулях,
      порог 70% (сейчас 87%)
- [x] [fact] ci.yml: шаг `pytest (MCP conformance, E2E stdio)`

## Доки и версия
- [x] [fact] docs/playbook.md → «MCP conformance» (методы, транспорт,
      формат ошибок, запуск)
- [x] [fact] README: conformance + --coverage в разделе «Тесты»
- [x] [fact] CHANGELOG 0.8.0, версия, план — Фаза 23 ✅

## Верификация
- [x] [assumption] pytest (все 276), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.8.0: TestPyPI → PyPI → GitHub Release
