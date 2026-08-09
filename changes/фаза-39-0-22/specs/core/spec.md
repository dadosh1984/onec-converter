# Spec: core

## Purpose
Улучшить DX и продуктовую подачу: демо-режим load, интерактивная оболочка,
стандартизированные цели Makefile, guardrail на коммиты и понятный
пятиминутный старт. Версия 0.22.0.

## Acceptance criteria
- [x] load --dry-run: печатает {dry_run, objects, mode, target, note} без
      записи файлов/отправки (тест: load_direct не вызывается)
- [x] repl.py: parse_command (tables/describe/query [WHERE]/help/exit),
      run_command (list tables, describe поля, выборка 20 строк), run_shell;
      CLI shell --source-dir
- [x] Makefile: lint/type/test/bdd/gates/bench/clean
- [x] .githooks/pre-commit: блок *.1CD (>50МБ)/extract.json/load.json/*.jsonl
- [x] README: «Быстрый старт за 5 минут», бейдж PyPI, shell-пример
- [x] Ворота: pytest (+5), conformance, ruff, mypy (50), check_bsl,
      vitest — зелёные; релиз 0.22.0
