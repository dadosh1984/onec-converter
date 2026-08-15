# Spec: core

## Назначение
Clean up onec-converter: fix remaining critical issues found by audit, remove duplicate code, phase labels, and deprecated patterns. Refactor duplicate pipeline into engine.py, remove CLI↔MCP duplication, clean up error hierarchy and global mutable state. Wave 1: surgery - move pipelone extract-transform-load into engine.py, make cli.py and mcp_server.py thin wrappers - check and fix any broken code - remove dead code Wave 2: historical noise - удалить Фаза/U/идея метки из docstrings - remove commented experiments - clean imports with ruff Wave 3: architectural - unify error hierarchy - remove global mutable state (audit.py _active, progress.py _active, mcp_server.py _SERVER_META_CACHE) - remove deprecated jwt_auth.py with DeprecationWarning

## Область

- В области: указанная возможность, поставляется тест-первой.
- Вне области: всё, что не заявлено в предложении.

## Критерии приёмки
- [ ] Заполнить в ходе реализации
