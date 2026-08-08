# Tasks — Фаза 29.1: сокращение MCP-туллов (15 → 12)

Ворота: mypy strict, ruff, pytest, vitest. Релиз 0.7.0. CLI не трогаем.

## Объединение тулов
- [x] [fact] `query_table` → удалён; остаётся `query_sql` (WHERE-совместим)
- [x] [fact] `table_sizes(..., format="json|xlsx", out_file, top_n)` — XLSX-режим
      вместо table_sizes_report (удалён)
- [x] [fact] `compare_structures(..., format="json|xlsx", out_file)` — XLSX-режим
      вместо structure_report (удалён)
- [x] [fact] плейбук/подсказки MCP: PLAYBOOK_NEXT, step '10' → query_sql

## Тесты
- [x] [fact] query_sql с WHERE-фильтром (бывший query_table сценарий)
- [x] [fact] table_sizes format='xlsx' (файл создаётся)
- [x] [fact] compare_structures format='xlsx' (файл; xlsx без out_file — ошибка)
- [x] [fact] playbook/next — согласованы (query_sql)

## Доки
- [x] [fact] README/playbook.md — query_sql, форматы; CHANGELOG 0.7.0;
      план — 29.1 ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.7.0: TestPyPI → PyPI → GitHub Release
