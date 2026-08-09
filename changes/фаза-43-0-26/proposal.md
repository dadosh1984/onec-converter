# Proposal — фаза-43-0-26

**Goal:** Фаза 43 (0.26.0) — SQL-источники до production-grade: (1) _connect() с connect_timeout (10 с по умолчанию, fallback на драйверы без kwarg); (2) fetch_rows() потоковая через fetchmany, для postgres — серверный курсор (psycopg2 named cursor) с fallback; (3) README «SQL-источники: ограничения» — честный контракт; (4) интеграционный тест PostgreSQL в CI (job sql-pg: сервис postgres:16, сид _Reference1, прогон test_phase43_sql_pg.py; локально skip без ONEC_TEST_PG_DSN); col_sql скобки уже в Фазе 41. Тесты +5 в tests/test_phase43_sql_pg.py (таймаут, fallback, потоковость, интеграция). CHANGELOG 0.26.0, план ✅, релиз.

- Platform: тесты в E:\test через gates.sh; версия 0.26.0; mypy только src; интеграционный PG-тест env-gated (skip без ONEC_TEST_PG_DSN)
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, mcp-python-1-7:forge:73e3469b3d99, mcp-python-1-7:forge:8518cd4a492d, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b
