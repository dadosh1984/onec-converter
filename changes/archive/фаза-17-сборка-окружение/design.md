# Design — Фаза 17: сборка и окружение (Enterprise-grade установка)

## Цель
`pip install -e ".[dev]"` и `bash scripts/gates.sh` работают на чистом клоне.
Устранить найденные анализами баги сборки/окружения. Авторский код.

## Задачи и решения

### 1. pyproject.toml — зависимости
- `mcp>=1.9,<2.0` (текущая установка 1.29.0; код совместим с 1.x). На 2.x
  `mcp.server.fastmcp` переписан — блокируем установку 2.x, пока нет порта.
- `PyYAML` в dependencies (нужен `dump_metadata(fmt='yaml')`).
- dev: добавить `types-olefile`, `types-openpyxl` (для mypy --strict).

### 2. scripts/gates.sh — условный vitest
- Ворота в порядке: pytest → ruff → mypy → vitest.
- `run_vitest` становится условным: если нет `package.json`/`*.test.ts`/node_modules —
  печатает `[skip] vitest (не настроен: нет package.json/*.test.ts)` и возвращает 0
  (не роняет прогон). Если файлы есть — полноценный `npx vitest run`.
- `--strict-steps` флаг опционален: если задан, skip-шаги роняют (для CI с фактическими тестами).

### 3. src/tasks/*.ts — чистка
- `git rm --cached src/tasks` (остаются в .gitignore), удалить с диска.
- Это агентные заглушки Orion; в git не должны жить.

### 4. LICENSE (MIT, авторский)
- Файл LICENSE с текстом MIT, copyright данные проекта.

### 5. Согласование docs
- `docs/backlog.md`: Фаза 14 — убрать противоречие (чек-лист должен отражать
  осознанный отказ, а не «сделано»); согласовать «Итог».
- `docs/roadmap.md`: отметить закрытые фазы 7–16 [x], убрать дезинформацию.

### 6. Команда `onec-converter doctor`
- Новая подкоманда в cli.py. Диагностика:
  - версия mcp (совместимость: 1.x ок, 2.x — предупреждение);
  - наличие PyYAML (для fmt=yaml);
  - доступность кеша (discа), свободное место в .onec_cache;
  - версия python.
- Выводит таблицу-статус, возвращает 0 если всё ок, >0 если есть проблемы.
- Не падает на отсутствующих компонентах — печатает и продолжается.

### 7. GitHub Actions
- `.github/workflows/ci.yml`: на push/PR — setup python 3.11, `pip install -e ".[dev]"`,
  `bash scripts/gates.sh ruff mypy pytest` (+ vitest если настроен).

## Модули
- `pyproject.toml`, `scripts/gates.sh`, `src/onec_converter/cli.py` (doctor),
  `.github/workflows/ci.yml`, `LICENSE`, `docs/backlog.md`, `docs/roadmap.md`,
  `docs/development-plan.md` (отметка прогресса).

## Верификация
- Локально: pip install -e . (чистая), gates.sh ruff mypy (vitest условный),
  pytest; cli doctor; согласованность docs.
- Ворота: pytest, ruff, mypy strict, vitest.
