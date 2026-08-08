# Proposal — фазу-24-полный-сценарий

**Goal:** Реализовать Фазу 24 Полный сценарий копии базы (clone-db + rollback) в onec-converter: модуль clone_db.py с clone_db(source_dir, target_dir, rules='') — полная побитовая копия 1Cv8.1CD, кеш-сброс Cache.drop по новому ключу, --with-rules (стенд); CLI подкоманда clone-db; снапшот до миграции в load_8x.load_direct (workdir/snapshot.1CD, параметр snapshot, возврат 'snapshot'), флаги --no-snapshot (CLI load) и no_snapshot (MCP load_direct); тесты (clone синтетика, rules, ошибки, CLI, snapshot/restore при сбое, no-snapshot, Cache.drop); docs/recipes стенд + README; CHANGELOG 0.9.0, релиз.

- Platform: any
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фаза-11-новая-порция:forge:537c39f668a9, фаза-11-новая-порция:forge:409e2a92d172, фаза-10-прямая-запись:forge:7b4be40d8e94, mcp-python-1-7:forge:64a0dea04a25
