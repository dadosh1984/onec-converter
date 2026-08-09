# Result — фаза-36-0-19

- **Status:** SUCCESS
- **Tasks:** 7/7 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:PASS, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** compact
- **Constraints:** compact
- **Generated:** 2026-08-09T00:01:05.616Z

## Checklist

- [x] [fact] sql_source.py: SqlSource (list_tables/fetch_metadata/fetch_rows),
- [x] [fact] adapters: ленивый importlib psycopg2/pyodbc, information_schema
- [x] [fact] extract --source-kind 1cd|postgres|mssql + --source-url
- [x] [fact] README — SQL-источники + spike-граница
- [x] [fact] тесты +5 на mock-драйвере (без реальных серверов)
- [x] [fact] CHANGELOG 0.19.0; план Фаза 36 ✅
- [x] [assumption] ворота зелёные; релиз 0.19.0

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  249 passed (249)
      Tests  249 passed (249)
   Duration  11.92s (transform 7.37s, setup 0ms, collect 16.79s, tests 921ms, environment 71ms, prepare 42.97s)

[orion: −28212 B (−99.3%) ≈ 7053 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | PASS | 13 snippet(s) within repo norms (median 9 LOC, 2 imports) |
| economy | PASS | cache 144.9 KB of 100.0 MB (597 entries) — within budget; ≈ 598021 tok saved across 439 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: ci, test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/фаза-36-0-19/proposal.md`
- `changes/фаза-36-0-19/design.md`
- `changes/фаза-36-0-19/tasks.md`
- `changes/фаза-36-0-19/forge-report.md`
- `reports/фаза-36-0-19/guard-report.md`
- `changes/фаза-36-0-19/specs/core/spec.md`
- `changes/фаза-36-0-19/snippets/`

## Уроки и решения

> task not green: [fact] CHANGELOG 0.19.0; план Фаза 36 ✅ — Command failed: npx vitest run tests/changelog_0_19.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/changelog_0_19.test.ts[2m > [22mchangelog_0_19[2m > [22mworks · [31m[1mTy → fix the task, then re-run orion forge фаза-36-0-19
> task not green: [fact] sql_source.py: SqlSource (list_tables/fetch_metadata/fetch_rows), — Command failed: npx vitest run tests/sql_source_py.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/sql_source_py.test.ts[2m > [22msql_source_py → fix the task, then re-run orion forge фаза-36-0-19
> [mcp-python-1-7] task not green: [assumption] `source_sql`: чтение серверной ИБ (MS SQL / PostgreSQL) через SQL; unit-тесты на in-memory БД — Command failed: pnpm vitest run tests/assumption_source_sql_ms_sql_postgresql_sql_unit_in_memory.test.ts · Error: C → fix the task, then re-run orion forge mcp-python-1-7
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter_2.test.ts[2m >  → fix the task, then re-run orion forge фаза-11-новая-порция
> [фазу-23-conformance-тесты] task not green: [fact] CHANGELOG 0.8.0, версия, план — Фаза 23 ✅ — Command failed: npx vitest run tests/changelog_0_8.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/changelog_0_8.test.ts[2m > [22mchangelog_0_8[2m > [22mworks · [31m → fix the task, then re-run orion forge фазу-23-conformance-тесты
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter.test.ts[2m > [22mcli → fix the task, then re-run orion forge фаза-11-новая-порция

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
