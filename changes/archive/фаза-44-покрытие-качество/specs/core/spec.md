# Spec: core

## Purpose
Расширить покрытие и качество: конфигурируемый список модулей покрытия
(в pyproject, с модулями Фаз 32-40), mypy strict на scripts/, политика
типизации tests/, UZ-профиль PII, тайминг ворот, мультифайловый check_bsl.
Версия 0.27.0.

## Acceptance criteria
- [x] pyproject.toml [tool.onec-gates]: coverage_modules (11 модулей,
      включая audit/clone_db/health/s3_client/sql_source/ai_skills) +
      coverage_threshold=70; gates.sh читает их оттуда
- [x] CI: шаг `gates.sh pytest --coverage` (порог реально прогоняется)
- [x] mypy: `python -m mypy src scripts` (55 файлов, strict)
- [x] README: политика — mypy strict на src/ и scripts/; tests/ осознанно
      не типизируются
- [x] PII_PROFILES['uzbekistan'] (ПИНФЛ/ИНН/паспорт/телефон); Anonymizer
      маскирует ПИНФЛ/ИНН; scan_text(profile='UZ') детектит pinfl+phone
- [x] gates.sh: тайминг pytest (== pytest: Ns ==) + предупреждение при
      PYTEST_TIME_LIMIT (180 с)
- [x] check_bsl.main([файлы]) обрабатывает несколько .bsl; тест на
      дубликат во втором файле
- [x] Ворота: pytest (+6), conformance, ruff, mypy (55), check_bsl,
      vitest — зелёные; релиз 0.27.0
