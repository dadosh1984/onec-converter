# Result — фаза-9-cli-обёртка

- **Status:** SUCCESS
- **Tasks:** 9/9 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:WARN, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** unset
- **Constraints:** none
- **Generated:** 2026-08-08T14:09:08.648Z

## Checklist

- [x] [fact] `cli.py`: argparse-подкоманды `inspect`, `extract`, `map`,
- [x] [assumption] `inspect`: метаданные источника (объекты, виды, таблицы,
- [x] [assumption] `extract`: чтение 7.7/8.x → intermediate JSON
- [x] [assumption] `map`: `--rules-file` (валидация TOON-правил) и
- [x] [assumption] `transform`: применение правил к intermediate
- [x] [assumption] `load`: загрузка батчей в приёмник
- [x] [assumption] `status`: состояние пайплайна в project-dir
- [x] [fact] pyproject: entry-point `onec-converter`; unit-тесты CLI
- [x] [assumption] README: раздел CLI с примерами каждой подкоманды

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  19 passed (19)
      Tests  19 passed (19)
   Duration  972ms (transform 675ms, setup 0ms, collect 1.27s, tests 69ms, environment 4ms, prepare 2.87s)

[orion: −2503 B (−92.5%) ≈ 626 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | WARN | 2 snippet(s) far above repo norms (median 75 LOC, 3 imports): changes\фаза-9-cli-обёртка\snippets\cli_py_argparse.ts: 331 LOC vs median 75 (4.4×) | changes\фаза-9-cli-обёртка\snippets\readme_раздел_cli.ts: 233 LOC vs median 75 (3.1×) |
| economy | PASS | cache 16.2 KB of 100.0 MB (54 entries) — within budget; ≈ 464488 tok saved across 352 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/фаза-9-cli-обёртка/proposal.md`
- `changes/фаза-9-cli-обёртка/design.md`
- `changes/фаза-9-cli-обёртка/tasks.md`
- `changes/фаза-9-cli-обёртка/forge-report.md`
- `reports/фаза-9-cli-обёртка/guard-report.md`
- `changes/фаза-9-cli-обёртка/specs/cli/spec.md`
- `changes/фаза-9-cli-обёртка/snippets/`

## Уроки и решения

> missing exported: cli_mcp_step_transform_validate_verify → fix the drift check, then re-run orion shield фаза-9-cli-обёртка
> [mcp-python-1-7] task not green: [assumption] `mcp_server`: тулы пайплайна init/inspect_source/extract/inspect_target/map/ — Command failed: pnpm vitest run tests/assumption_mcp_server_init_inspect_source_extract_inspect_target.test.ts · Error: Command fail → fix the task, then re-run orion forge mcp-python-1-7
> [mcp-python-1-7] task not green: [assumption] Scaffold проекта: `pyproject.toml`, ruff, mypy, pytest, зависимости (mcp SDK, olefile, openpyxl, httpx) — Command failed: pnpm vitest run tests/assumption_scaffold_pyproject_toml_ruff_mypy_pytest_mcp_sdk_olef.te → fix the task, then re-run orion forge mcp-python-1-7
> [фаза-7-сквозной-перенос] missing exported: read-only-mypy-strict-ruff-pytest-http-m → fix the drift check, then re-run orion shield фаза-7-сквозной-перенос
> [mcp-python-1-7] task not green: [assumption] `mapping`: JSON-схема правил (объекты, реквизиты, перечисления); LLM-генерация правил по метаданным обеих сторон (промпт-шаблон); unit-тесты — Command failed: pnpm vitest run tests/assumption_mapping_json_llm_un → fix the task, then re-run orion forge mcp-python-1-7
> [фаза-8-xlsx-отчёты] missing exported: read-only-mypy-strict-ruff-pytest-openpy → fix the drift check, then re-run orion shield фаза-8-xlsx-отчёты

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
