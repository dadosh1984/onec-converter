# Proposal — фазу-29-1-сокращение

**Goal:** Реализовать Фазу 29.1 сокращение MCP-туллов в onec-converter: объединить query_table→query_sql (удалить старый), table_sizes/table_sizes_report→table_sizes --format json|xlsx, structure_report/compare_structures→compare_structures --format json|xlsx (15→12 тулов). CLI-поверхность не трогаем. Обновить плейбук/подсказки MCP, тесты (query_sql вместо query_table, xlsx-режимы), README/playbook docs, CHANGELOG 0.7.0. Ворота зелёные, релиз 0.7.0.

- Platform: any
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9, orion-spec:session:4d99052ba17f, фаза-11-новая-порция:forge:1cab45743c7e, фаза-11-новая-порция:forge:4ef85179cfd1
