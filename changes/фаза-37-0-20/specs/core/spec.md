# Spec: core

## Purpose
Добавить слой безопасности и комплаенса: сканер ПДн (RU/UZ), tamper-evident
аудит, маскирование ПДн в журнале, RBAC для MCP и отчёт 152-ФЗ/152 УЗ.
Версия 0.20.0.

## Acceptance criteria
- [x] pii_scanner: ИНН (10/12), СНИЛС, карты (Luhn), телефоны (RU/+998),
      ПИНФЛ (UZ), e-mail; scan_text/scan_value/scan_record/field_is_pii
- [x] audit: record добавляет prev_hash/hash; verify_audit ловит подмену
      записи/обрыва цепочки; продолжение цепочки при перезапуске
- [x] audit pii_masking: obj/detail/guid проходят _redact (ПДн -> ***);
      CLI --pii-masking на extract/transform/load
- [x] RBAC MCP: ONEC_MCP_ROLE=inspect|load; load_direct требует load;
      RbacError; default=load (backward-compat)
- [x] gdpr_152_report + CLI pii-report: перечень ПДн-полей, алгоритмы,
      tamper_evident, место логов
- [x] Ворота: pytest (+10), conformance, ruff, mypy (48), check_bsl,
      vitest — зелёные; релиз 0.20.0
