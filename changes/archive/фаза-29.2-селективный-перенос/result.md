# Result — селективный-перенос-разделам-фаза

- **Status:** SUCCESS
- **Tasks:** 10/10 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:PASS, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** compact
- **Constraints:** compact
- **Generated:** 2026-08-08T20:51:31.412Z

## Checklist

- [x] [fact] `objects_filter.py`: ObjectSpec + parse_objects (Раздел.Имя,
- [x] [fact] CLI `extract --objects`: проброс в 7.7 (Справочник.<id>) и 8.x
- [x] [fact] MCP `step_extract(objects="")` — селективный перенос
- [x] [fact] unit: парсер/матчер (точно/группы/Таблица/ошибки)
- [x] [fact] CLI 8.x на fake-базе: Таблица._REFERENCE3; неверный формат → rc=1
- [x] [fact] реальная база 8.1 (read-only): маппинг групп Справочник.*
- [x] [fact] MCP: step_extract с objects (группа/точный/нет раздела)
- [x] [fact] README (селективный перенос), CHANGELOG 0.6.0, план — задача ✅
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.6.0: TestPyPI → PyPI → GitHub Release

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  136 passed (136)
      Tests  136 passed (136)
   Duration  5.95s (transform 2.62s, setup 0ms, collect 6.14s, tests 457ms, environment 36ms, prepare 21.75s)

[orion: −15701 B (−98.7%) ≈ 3925 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | PASS | 14 snippet(s) within repo norms (median 9 LOC, 2 imports) |
| economy | PASS | cache 97.3 KB of 100.0 MB (343 entries) — within budget; ≈ 510606 tok saved across 409 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: ci, test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/селективный-перенос-разделам-фаза/proposal.md`
- `changes/селективный-перенос-разделам-фаза/design.md`
- `changes/селективный-перенос-разделам-фаза/tasks.md`
- `changes/селективный-перенос-разделам-фаза/forge-report.md`
- `reports/селективный-перенос-разделам-фаза/guard-report.md`
- `changes/селективный-перенос-разделам-фаза/specs/core/spec.md`
- `changes/селективный-перенос-разделам-фаза/snippets/`

## Уроки и решения

> task not green: [fact] MCP: step_extract с objects (группа/точный/нет раздела) — Command failed: npx vitest run tests/mcp_step_extract_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/mcp_step_extract_2.test.ts[2m > [22mmcp_step_extra → fix the task, then re-run orion forge селективный-перенос-разделам-фаза
> task not green: [fact] реальная база 8.1 (read-only): маппинг групп Справочник.* — Command failed: npx vitest run tests/реальная_база_8.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/реальная_база_8.test.ts[2m > [22mреальная_база_8[2 → fix the task, then re-run orion forge селективный-перенос-разделам-фаза
> task not green: [fact] MCP `step_extract(objects="")` — селективный перенос — Command failed: npx vitest run tests/mcp_step_extract.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/mcp_step_extract.test.ts[2m > [22mmcp_step_extract[2m  → fix the task, then re-run orion forge селективный-перенос-разделам-фаза
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter.test.ts[2m > [22mcli → fix the task, then re-run orion forge фаза-11-новая-порция
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter_2.test.ts[2m >  → fix the task, then re-run orion forge фаза-11-новая-порция

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
