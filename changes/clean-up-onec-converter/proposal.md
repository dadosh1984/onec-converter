# Предложение — clean-up-onec-converter

## Цель
Clean up onec-converter: fix remaining critical issues found by audit, remove duplicate code, phase labels, and deprecated patterns. Refactor duplicate pipeline into engine.py, remove CLI↔MCP duplication, clean up error hierarchy and global mutable state. Wave 1: surgery - move pipelone extract-transform-load into engine.py, make cli.py and mcp_server.py thin wrappers - check and fix any broken code - remove dead code Wave 2: historical noise - удалить Фаза/U/идея метки из docstrings - remove commented experiments - clean imports with ruff Wave 3: architectural - unify error hierarchy - remove global mutable state (audit.py _active, progress.py _active, mcp_server.py _SERVER_META_CACHE) - remove deprecated jwt_auth.py with DeprecationWarning

## Контекст

| Аспект | Значение |
|--------|----------|
| Платформа | any |
| Бюджет | compact |
| Ограничения | compact |

- **Lessons applied (v0.12):** скилл-onec-converter-migration:forge:d89d5187918c, фазу-25-audit-логирование:forge:4a67fe76ecf6, фазу-25-audit-логирование:forge:324392fa7f84, фаза-51-0-34:forge:f489239cac79, фаза-37-0-20:forge:f966453280f8
