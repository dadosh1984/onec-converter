# Result — фаза-11-новая-порция

- **Status:** SUCCESS
- **Tasks:** 8/8 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:WARN, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** unset
- **Constraints:** none
- **Generated:** 2026-08-08T14:59:32.613Z

## Checklist

- [x] [spike] Пересмотр блок-листа + формат: PARAMS/IBVERSION/CONFIG/CONFIGSAVE/
- [x] [fact] `query.py`: `query_table_sql(db, table, select, where, order_by,
- [x] [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты
- [x] [fact] `guid_diff.py`: `guid_diff(source_dir, target_dir)` — объекты и
- [x] [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты
- [x] [fact] `config_versions.py`: `config_versions(path)` — формат, версия ИБ/
- [x] [assumption] CLI `onec-converter config-versions` + MCP-тул `config_versions`;
- [x] [assumption] README: раздел «Фаза 11» со статусами (E1–E3 + пересмотр

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  33 passed (33)
      Tests  33 passed (33)
   Duration  2.75s (transform 1.61s, setup 0ms, collect 3.07s, tests 142ms, environment 15ms, prepare 9.88s)

[orion: −4066 B (−95.2%) ≈ 1017 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 2 exported capabilities |
| yagni | WARN | 9 snippet(s) far above repo norms (median 1 LOC, 0 imports): changes\фаза-11-новая-порция\snippets\cli_onec_converter.ts: 86 LOC vs median 1 (86.0×) | changes\фаза-11-новая-порция\snippets\cli_onec_converter_2.ts: 86 LOC vs median 1 (86.0×) | changes\фаза-11-новая-порция\snippets\cli_onec_converter_3.ts: 86 LOC vs median 1 (86.0×) | changes\фаза-11-новая-порция\snippets\config_versions_py.ts: 100 LOC vs median 1 (100.0×) | changes\фаза-11-новая-порция\snippets\guid_diff_py.ts: 98 LOC vs median 1 (98.0×) | changes\фаза-11-новая-порция\snippets\query_py_query.ts: 162 LOC vs median 1 (162.0×) | changes\фаза-11-новая-порция\snippets\readme_раздел_фаза.ts: 181 LOC vs median 1 (181.0×) | changes\фаза-11-новая-порция\snippets\spike_пересмотр_блок.ts: 36 LOC vs median 1 (36.0×) | changes\фаза-11-новая-порция\snippets\tests_phase11.ts: 301 LOC vs median 1 (301.0×) |
| economy | PASS | cache 32.4 KB of 100.0 MB (95 entries) — within budget; ≈ 470722 tok saved across 369 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/фаза-11-новая-порция/proposal.md`
- `changes/фаза-11-новая-порция/design.md`
- `changes/фаза-11-новая-порция/tasks.md`
- `changes/фаза-11-новая-порция/forge-report.md`
- `reports/фаза-11-новая-порция/guard-report.md`
- `changes/фаза-11-новая-порция/specs/core/spec.md`
- `changes/фаза-11-новая-порция/specs/phase11_ideas/spec.md`
- `changes/фаза-11-новая-порция/snippets/`

## Уроки и решения

> invalid capability name(s): фаза_11_идеи — "# Spec:" headings must be valid JS identifiers matching an export in src/tasks (rename the heading to the exported module's name, e.g. "# Spec: core" for src/tasks/core.ts) → fix the drift check, then re-run orion shield фаза-11-новая-порция
> Command failed: pnpm exec tsc --noEmit
 → fix the type check, then re-run orion shield фаза-11-новая-порция
> task not green: [assumption] README: раздел «Фаза 11» со статусами (E1–E3 + пересмотр — Command failed: npx vitest run tests/readme_раздел_фаза.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/readme_раздел_фаза.test.ts[2m > [22mreadme_ → fix the task, then re-run orion forge фаза-11-новая-порция
> task not green: [assumption] CLI `onec-converter config-versions` + MCP-тул `config_versions`; — Command failed: npx vitest run tests/cli_onec_converter_3.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter_3.test.ts[2m > → fix the task, then re-run orion forge фаза-11-новая-порция
> task not green: [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter_2.test.ts[2m >  → fix the task, then re-run orion forge фаза-11-новая-порция
> task not green: [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter.test.ts[2m > [22mcli → fix the task, then re-run orion forge фаза-11-новая-порция
> task not green: [fact] `query.py`: `query_table_sql(db, table, select, where, order_by, — Command failed: npx vitest run tests/query_py_query.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/query_py_query.test.ts[2m > [22mquery_py_quer → fix the task, then re-run orion forge фаза-11-новая-порция
> task not green: [spike] Пересмотр блок-листа + формат: PARAMS/IBVERSION/CONFIG/CONFIGSAVE/ — Command failed: npx vitest run tests/spike_пересмотр_блок.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/spike_пересмотр_блок.test.ts[2m > [2 → fix the task, then re-run orion forge фаза-11-новая-порция
> [фаза-7-сквозной-перенос] missing exported: read-only-mypy-strict-ruff-pytest-http-m → fix the drift check, then re-run orion shield фаза-7-сквозной-перенос
> [фаза-8-xlsx-отчёты] missing exported: read-only-mypy-strict-ruff-pytest-openpy → fix the drift check, then re-run orion shield фаза-8-xlsx-отчёты
> [migrate-tool-e2e-pipeline] missing exported: read_only_mypy_strict_ruff_pytest_http_m → fix the drift check, then re-run orion shield migrate-tool-e2e-pipeline
> [migrate-tool-e2e-pipeline] invalid capability name(s): read-only-mypy-strict-ruff-pytest-http-m — "# Spec:" headings must be valid JS identifiers matching an export in src/tasks (rename the heading to the exported module's name, e.g. "# Spec: core" for src/tasks/core → fix the drift check, then re-run orion shield migrate-tool-e2e-pipeline

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
