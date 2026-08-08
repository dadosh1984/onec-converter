# Spec: core

## Purpose
Реализовать Фазу 25 Audit-логирование миграции в onec-converter: модуль audit.py (AuditLog JSONL: время/уровень INFO|WARN|ERROR/операция/объект/GUID/правило/результат; set_audit/get_audit, env ONEC_AUDIT_FILE для MCP; read_audit); интеграция load_direct (событие на каждый объект с GUID приёмника + WARN по ссылкам + сводка), CLI transform/extract (по-объектно, error-события при TransformError), MCP step_extract; CLI --audit-file на extract/transform/load + подкоманда audit (--file/--level/--op/--obj/--tail/--json, сводка); тесты (+6): журнал/уровни/JSONL, load_direct, transform ok+error, extract, CLI-фильтры; docs playbook «Аудит переноса (ПДн)» + README; CHANGELOG 0.10.0, релиз.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
