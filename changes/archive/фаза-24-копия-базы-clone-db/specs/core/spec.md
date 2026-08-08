# Spec: core

## Purpose
Реализовать Фазу 24 Полный сценарий копии базы (clone-db + rollback) в onec-converter: модуль clone_db.py с clone_db(source_dir, target_dir, rules='') — полная побитовая копия 1Cv8.1CD, кеш-сброс Cache.drop по новому ключу, --with-rules (стенд); CLI подкоманда clone-db; снапшот до миграции в load_8x.load_direct (workdir/snapshot.1CD, параметр snapshot, возврат 'snapshot'), флаги --no-snapshot (CLI load) и no_snapshot (MCP load_direct); тесты (clone синтетика, rules, ошибки, CLI, snapshot/restore при сбое, no-snapshot, Cache.drop); docs/recipes стенд + README; CHANGELOG 0.9.0, релиз.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
