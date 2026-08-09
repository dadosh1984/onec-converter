# Tasks — Фаза 37: Безопасность и комплаенс (0.20.0)

## PII-сканирование
- [x] [fact] pii_scanner.py: ИНН/СНИЛС/карты(Луна)/тел(RU+UZ)/ПИНФЛ/e-mail;
      scan_text/scan_record/field_is_pii; профиль UZ

## Аудит
- [x] [fact] audit: tamper-evident SHA-256 hash-цепочка + verify_audit
- [x] [fact] audit: pii_masking (скрытие ПДн в obj/detail/guid); --pii-masking

## RBAC
- [x] [fact] rbac_mcp: ONEC_MCP_ROLE, load_direct требует load; RbacError

## Отчёт
- [x] [fact] gdpr_152_report.py + CLI pii-report (--audit-file --rules-file --profile)

## Доки / релиз
- [x] [fact] тесты +10; README, commands-map CLI 22; CHANGELOG 0.20.0
- [x] [assumption] ворота зелёные; релиз 0.20.0
