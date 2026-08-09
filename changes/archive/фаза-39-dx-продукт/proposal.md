# Proposal — фаза-39-0-22

**Goal:** Фаза 39 (0.22.0) — DX и продукт onec-converter: (1) --dry-run глобально для load --direct/--http (демо-план: сколько объектов/таблиц, режим, без записи/отправки), флаг на load; тест что ничего не пишется; (2) `shell --source-dir`: интерактивный REPL для исследования базы (readline, команды: tables, query, help, exit; автодополнение имён таблиц); модуль repl.py + CLI; (3) Makefile (lint/bdd/release/pm); (4) pre-commit hook (git hook blocking .1CD / extract.json / *.jsonl с ПДн в коммит); (5) README: «Быстрый старт за 5 минут» вверху; PyPI уже на видном; release notes на русском (уже). Тесты: dry-run load не пишет, repl парсер команд (без интерактивного ввода), Makefile существует с целями. CHANGELOG 0.22.0, план ✅, релиз.

- Platform: тесты в E:\test через gates.sh; версия 0.22.0; mypy только src; shell REPL без внешних зависимостей
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b
