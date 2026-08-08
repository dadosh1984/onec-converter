# Tasks — Фаза 17: сборка и окружение

Ворота: mypy strict, ruff, pytest, vitest. Авторский код.

## pyproject / зависимости
- [x] [fact] pyproject: `mcp>=1.9,<2.0`, добавить `PyYAML` в dependencies
- [x] [fact] pyproject dev: добавить `types-olefile`, `types-openpyxl`

## gates.sh — условный vitest
- [x] [fact] run_vitest: если нет package.json/*.test.ts/node_modules — skip-предупреждение + exit 0; иначе npx vitest run
- [x] [fact] флаг `--strict-steps`: при заданном — skip-шаги fail (для CI)

## Чистка src/tasks из git
- [x] [fact] `git rm --cached src/tasks` + удалить с диска; .gitignore остаётся

## LICENSE
- [x] [fact] LICENSE (MIT, авторский текст)

## Согласование docs
- [x] [fact] docs/backlog.md: Фаза 14 — чек-лист отражает осознанный отказ (НЕ «сделано»), согласовать с «Итогом»
- [x] [fact] docs/roadmap.md: отметить закрытые фазы 7–16 [x], убрать незакрытые [ ] для сделанного

## Команда doctor
- [x] [fact] cli.py: подкоманда `doctor` — диагностика (версия mcp 1.x/2.x, PyYAML, python, кеш/место на диске)
- [x] [fact] тест test_cli_doctor.py: доктор возвращает 0 при ок-окружении, не падает при отсутствии yaml, покрывает вызов

## CI
- [x] [fact] .github/workflows/ci.yml: push/PR → python 3.11, pip install -e ".[dev]", gates.sh ruff mypy pytest (vitest если настроен)

## Верификация
- [x] [assumption] pip install -e . (чисто), gates.sh ruff/mypy, pytest, cli doctor — зелёные
- [x] [assumption] docs согласованы; src/tasks отсутствует в git
