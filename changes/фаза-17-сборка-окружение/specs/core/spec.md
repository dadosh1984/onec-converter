# Spec: core

## Purpose
Фаза 17 — сборка и окружение: `pip install -e ".[dev]"` и `bash scripts/gates.sh`
работают на чистом клоне. Устранить найденные анализами баги сборки.

## Requirements
- [REQ-1] pyproject: `mcp>=1.9,<2.0` (исключить 2.x), добавить `PyYAML` в
  dependencies; dev — `types-olefile`, `types-openpyxl`.
- [REQ-2] `scripts/gates.sh`: vitest условный (skip если не настроен, exit 0);
  флаг `--strict-steps` делает skip-шаги фатальными.
- [REQ-3] `src/tasks/*.ts` удалены из git (остаются gitignored на диске для vitest).
- [REQ-4] LICENSE (MIT, авторский).
- [REQ-5] docs/backlog.md + docs/roadmap.md согласованы (Фаза 14 — осознанный
  отказ; закрытые фазы отмечены [x]).
- [REQ-6] Команда `onec-converter doctor`: диагностика (версия mcp, PyYAML,
  python, кеш) — exit 0 при ок, >0 при проблемах; не падает.
- [REQ-7] GitHub Actions: push/PR → ruff, mypy, pytest.
- [REQ-8] Ворота зелёные: pytest, ruff, mypy strict, vitest.
