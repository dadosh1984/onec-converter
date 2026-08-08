# Spec: core

## Purpose
Реализовать Фазу 23 Conformance-тесты MCP + CI-гейты в onec-converter: tests/test_mcp_conformance.py (5 E2E-проверок через stdio-клиент mcp 1.x: initialize, tools/list, tools/call, изолированная ошибка неизвестного тула, поле next), scripts/gates.sh цель conformance и флаг --coverage (pytest-cov порог 70% на новых модулях objects_filter/jwt_auth/cache/http_client/mcp_server), шаг conformance в .github/workflows/ci.yml, раздел docs/playbook.md, README. Также устранён root-cause дисковой проблемы: pytest без --basetemp писал копии базы в %TEMP% на C: (24G мусора), теперь прогоны только через gates.sh. Версия 0.8.0, релиз.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
