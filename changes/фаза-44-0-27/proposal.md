# Proposal — фаза-44-0-27

**Goal:** Фаза 44 (0.27.0) — покрытие и качество: (1) COVERAGE_MODULES перенесён в pyproject.toml [tool.onec-gates] и расширен на audit/clone_db/health/s3_client/sql_source/ai_skills (все 88-97%); gates.sh читает список и порог оттуда; CI: шаг gates.sh pytest --coverage; (2) mypy strict на scripts/ (gates.sh: python -m mypy src scripts); (3) политика mypy tests/ задокументирована в README (tests/ осознанно не типизируются); (4) PII_PROFILES 'uzbekistan' (ПИНФЛ/ИНН/паспорт) + тесты маскирования (Anonymizer.apply) и scan_text(profile='UZ'); (5) gates.sh тайминг pytest + PYTEST_TIME_LIMIT (180 с); (6) check_bsl тест на несколько .bsl. Тесты +6 в tests/test_phase44_quality.py. CHANGELOG 0.27.0, план ✅, релиз.

- Platform: тесты в E:\test через gates.sh; версия 0.27.0; mypy src+scripts; COVERAGE_MODULES в pyproject [tool.onec-gates]
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, mcp-python-1-7:forge:01528e6c32f6, mcp-python-1-7:forge:73e3469b3d99, фаза-7-сквозной-перенос:shield:be4adfcf0907
