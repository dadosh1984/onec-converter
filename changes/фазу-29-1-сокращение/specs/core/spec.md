# Spec: core

## Purpose
Реализовать Фазу 29.1 сокращение MCP-туллов в onec-converter: объединить query_table→query_sql (удалить старый), table_sizes/table_sizes_report→table_sizes --format json|xlsx, structure_report/compare_structures→compare_structures --format json|xlsx (15→12 тулов). CLI-поверхность не трогаем. Обновить плейбук/подсказки MCP, тесты (query_sql вместо query_table, xlsx-режимы), README/playbook docs, CHANGELOG 0.7.0. Ворота зелёные, релиз 0.7.0.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
