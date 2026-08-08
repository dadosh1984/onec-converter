# Tasks — Фаза 25: Audit-логирование миграции

Ворота: mypy strict, ruff, pytest, vitest. Релиз 0.10.0.

## audit.py
- [x] [fact] AuditLog: JSONL-записи (ts/level/operation/obj/guid/rule/result/detail),
      уровни INFO|WARN|ERROR (иначе ValueError)
- [x] [fact] set_audit/get_audit (глобальный журнал), read_audit;
      env ONEC_AUDIT_FILE — для MCP

## Интеграция
- [x] [fact] load_direct: событие на каждый объект (GUID приёмника),
      WARN по ref_warnings, сводка total
- [x] [fact] CLI transform/extract: по-объектно; TransformError → ERROR-событие
- [x] [fact] MCP step_extract: по-объектно (не-stream) / сводно (stream)

## CLI
- [x] [fact] --audit-file (extract/transform/load), активация в main
- [x] [fact] подкоманда audit: --file/--level/--op/--obj/--tail/--json + сводка

## Тесты и доки
- [x] [fact] тесты (+6): журнал/уровни/JSONL, load_direct, transform ok+error,
      extract, CLI-фильтры
- [x] [fact] docs/playbook.md → «Аудит переноса (ПДн)»; README — audit
- [x] [fact] CHANGELOG 0.10.0, версия, план — Фаза 25 ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.10.0: TestPyPI → PyPI → GitHub Release
