# Proposal — фаза-40-0-23

**Goal:** Фаза 40 (0.23.0) — AI-навыки (детерминированные, без внешних LLM) в onec-converter: (1) MCP-тул auto_map_schemas: авто-маппинг полей между метаданными источника и приёмника по нормализованному имени/синониму (source_attr -> target_attr), возвращает правила TOON (файл rules.json как предложение); на основе read_metadata обеих баз; (2) MCP-тул explain_diff: человекочитаемые причины расхождений структур (поле только в источнике/приёмнике, изменение типа) из diff_structures; (3) skill context_compressor: сжатие метаданных (5000+ таблиц) до короткого саммари для LLM — функция compress_metadata (kind, count, топ-таблиц по объёму); (4) skill/examples: autonomous_migration — готовый сквозной сценарий командами CLI (пример в docs/ или examples/). Тесты: auto_map_schemas (маппинг по именам/синонимам, генерирует rules), explain_diff (причины), compress_metadata (саммари). CHANGELOG 0.23.0, план ✅, релиз. Это последняя фаза набора 32-40.

- Platform: тесты в E:\test через gates.sh; версия 0.23.0; mypy только src; без внешних LLM-зависимостей (детерминированные эвристики)
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-24-полный-сценарий:forge:1b6dbaa2498b, фазу-23-conformance-тесты:forge:753265ca3073, фаза-11-новая-порция:forge:537c39f668a9, фазу-25-audit-логирование:forge:7c216dc57da7, фаза-11-новая-порция:forge:409e2a92d172
