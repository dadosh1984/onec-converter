# Result — фаза-32-0-15

- **Status:** SUCCESS
- **Tasks:** 11/11 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:PASS, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** compact
- **Constraints:** compact
- **Generated:** 2026-08-08T23:26:20.413Z

## Checklist

- [x] [fact] clone_db: file_key(dst) ДО copy2, дроп старого ключа; тест
- [x] [fact] cache: тест TTL-эвикции (get/has не возвращают stale)
- [x] [fact] base_health: include_rows=False, sample_tables=N; тесты
- [x] [fact] check_bsl в gates.sh (цель bsl + all)
- [x] [fact] audit: один handle + flush + ротация; тесты
- [x] [fact] notify: retry с backoff; тесты
- [x] [fact] openapi BearerAuth + тест соответствия путям
- [x] [fact] CLI extract → save_json_stream; тест
- [x] [fact] Module.bsl Совпадает (constant-time X-API-Key)
- [x] [fact] CHANGELOG 0.15.0; план Фаза 32 ✅
- [x] [assumption] ворота зелёные; релиз 0.15.0

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  227 passed (227)
      Tests  227 passed (227)
   Duration  11.96s (transform 5.02s, setup 0ms, collect 11.64s, tests 1.01s, environment 78ms, prepare 46.05s)

[orion: −25709 B (−99.2%) ≈ 6427 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | PASS | 20 snippet(s) within repo norms (median 9 LOC, 2 imports) |
| economy | PASS | cache 131.2 KB of 100.0 MB (546 entries) — within budget; ≈ 570776 tok saved across 431 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: ci, test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/фаза-32-0-15/proposal.md`
- `changes/фаза-32-0-15/design.md`
- `changes/фаза-32-0-15/tasks.md`
- `changes/фаза-32-0-15/forge-report.md`
- `reports/фаза-32-0-15/guard-report.md`
- `changes/фаза-32-0-15/specs/core/spec.md`
- `changes/фаза-32-0-15/snippets/`

## Уроки и решения

> invalid capability name(s): Дефекты по итогам анализа (Фаза 32) — "# Spec:" headings must be valid JS identifiers matching an export in src/tasks (rename the heading to the exported module's name, e.g. "# Spec: core" for src/tasks/core.ts) → fix the drift check, then re-run orion shield фаза-32-0-15
> task not green: [fact] notify: retry с backoff; тесты — Command failed: npx vitest run tests/notify_retry_backoff.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/notify_retry_backoff.test.ts[2m > [22mnotify_retry_backoff[2m > [22mwor → fix the task, then re-run orion forge фаза-32-0-15
> task not green: [fact] audit: один handle + flush + ротация; тесты — Command failed: npx vitest run tests/audit_один_handle.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/audit_один_handle.test.ts[2m > [22maudit_один_handle[2m > [22 → fix the task, then re-run orion forge фаза-32-0-15
> task not green: [fact] check_bsl в gates.sh (цель bsl + all) — Command failed: npx vitest run tests/check_bsl_gates.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/check_bsl_gates.test.ts[2m > [22mcheck_bsl_gates[2m > [22mworks · [3 → fix the task, then re-run orion forge фаза-32-0-15
> task not green: [fact] cache: тест TTL-эвикции (get/has не возвращают stale) — Command failed: npx vitest run tests/cache_тест_ttl.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/cache_тест_ttl.test.ts[2m > [22mcache_тест_ttl[2m > [2 → fix the task, then re-run orion forge фаза-32-0-15
> task not green: [fact] clone_db: file_key(dst) ДО copy2, дроп старого ключа; тест — Command failed: npx vitest run tests/clone_db_file.test.ts · [31m[1m[7m FAIL [27m[22m[39m tests/clone_db_file.test.ts[2m > [22mclone_db_file[2m >  → fix the task, then re-run orion forge фаза-32-0-15
> [фаза-6-внедрить-идеи] [orion] 15 failing line(s):
 FAIL  tests/assumption_1cd_build_fake_1cd_path_tables_rows_1cdbmsv8_root_fat.test.ts [ tests/assumption_1cd_build_fake_1cd_path_tables_rows_1cdbmsv8_root_fat.t … [+8 ch]
 ❯ loadAndTransform node_modules/.pnpm/vi → fix the test check, then re-run orion shield фаза-6-внедрить-идеи

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
