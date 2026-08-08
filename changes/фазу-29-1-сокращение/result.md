# Result — фазу-29-1-сокращение

- **Status:** SUCCESS
- **Tasks:** 11/11 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:PASS, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** compact
- **Constraints:** compact
- **Generated:** 2026-08-08T21:03:08.538Z

## Checklist

- [x] [fact] `query_table` → удалён; остаётся `query_sql` (WHERE-совместим)
- [x] [fact] `table_sizes(..., format="json|xlsx", out_file, top_n)` — XLSX-режим
- [x] [fact] `compare_structures(..., format="json|xlsx", out_file)` — XLSX-режим
- [x] [fact] плейбук/подсказки MCP: PLAYBOOK_NEXT, step '10' → query_sql
- [x] [fact] query_sql с WHERE-фильтром (бывший query_table сценарий)
- [x] [fact] table_sizes format='xlsx' (файл создаётся)
- [x] [fact] compare_structures format='xlsx' (файл; xlsx без out_file — ошибка)
- [x] [fact] playbook/next — согласованы (query_sql)
- [x] [fact] README/playbook.md — query_sql, форматы; CHANGELOG 0.7.0;
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.7.0: TestPyPI → PyPI → GitHub Release

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  146 passed (146)
      Tests  146 passed (146)
   Duration  7.24s (transform 4.54s, setup 0ms, collect 11.85s, tests 520ms, environment 42ms, prepare 24.90s)

[orion: −16825 B (−98.8%) ≈ 4206 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | PASS | 17 snippet(s) within repo norms (median 9 LOC, 2 imports) |
| economy | PASS | cache 100.4 KB of 100.0 MB (365 entries) — within budget; ≈ 514812 tok saved across 411 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: ci, test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/фазу-29-1-сокращение/proposal.md`
- `changes/фазу-29-1-сокращение/design.md`
- `changes/фазу-29-1-сокращение/tasks.md`
- `changes/фазу-29-1-сокращение/forge-report.md`
- `reports/фазу-29-1-сокращение/guard-report.md`
- `changes/фазу-29-1-сокращение/specs/core/spec.md`
- `changes/фазу-29-1-сокращение/snippets/`

## Уроки и решения

> task not green: [fact] compare_structures format='xlsx' (файл; xlsx без out_file — ошибка) — Command failed: npx vitest run tests/compare_structures_format_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/compare_structures_format_2.tes → fix the task, then re-run orion forge фазу-29-1-сокращение
> task not green: [fact] `compare_structures(..., format="json|xlsx", out_file)` — XLSX-режим — Command failed: npx vitest run tests/compare_structures_format.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/compare_structures_format.test.t → fix the task, then re-run orion forge фазу-29-1-сокращение
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter query` + MCP-тул `query_sql`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter.test.ts[2m > [22mcli → fix the task, then re-run orion forge фаза-11-новая-порция
> [фаза-11-новая-порция] task not green: [assumption] CLI `onec-converter guid-diff` + MCP-тул `guid_diff`; unit-тесты — Command failed: npx vitest run tests/cli_onec_converter_2.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cli_onec_converter_2.test.ts[2m >  → fix the task, then re-run orion forge фаза-11-новая-порция
> [orion-spec] bash: === RTK learn README ===
# Learn — CLI Correction Detection

> See also [docs/contributing/TECHNICAL.md](../../docs/contributing/TECHNICAL.md) for the full architecture overview

## Purpose

Analyzes Claude Code session history  → use: cd /tmp/compare && ls gsd-core/commands/gsd/ && echo "---" && head -50 gsd-core/commands/gsd/gsd.md 2>/dev/null || ls gsd-core/commands/gsd/ | head -30

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
