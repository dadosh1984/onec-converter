# Proposal — фаза-50-0-33

**Goal:** Фаза 50 (0.33.0) — покрытие и тесты (раунд 5): (1) coverage_modules +9 (kd3_export, sonar_report, gdpr_152_report, source_techlog, notify, terminal, strict, type_priority), итог 90%; (2) dedicated-тесты 9 модулей в tests/test_phase50_coverage.py (+18); (3) strict fix: ref-поля валидируются для любых значений; (4) property round-trip fake-1CD (seeded); (5) hypothesis fuzz cache/strict, dep hypothesis>=6; (6) gates.sh benchmark с порогами BENCH_META_MS_MAX/BENCH_READ_MS_MAX (U49); (7) Windows CI-джоба (U48); (8) fix gates.sh CRLF coverage-модулей и PYTHONPATH=src; real-base e2e размечены integration и исключены из coverage-замера; тесты переведены на E:\tmp, очищен C:/tmp (31G). Ворота: pytest 482 (1 skip), coverage 90%. CHANGELOG 0.33.0, план ✅, релиз.

- Platform: тесты в E:\tmp; версия 0.33.0; ворота: pytest 482, coverage 90%
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фаза-8-xlsx-отчёты:shield:2aa0eefd02e7, фаза-7-сквозной-перенос:shield:be4adfcf0907, фазу-24-полный-сценарий:forge:1b6dbaa2498b, фаза-44-0-27:forge:4a2c37d241f3
