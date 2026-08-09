# Spec: core

## Purpose
Добавить детерминированные AI-навыки для LLM-агентов: авто-маппинг схем,
объяснение расхождений, сжатие метаданных и готовые сценарии. Без внешних
LLM-зависимостей (чистые эвристики/нормализация имён). Версия 0.23.0.

## Acceptance criteria
- [x] ai_skills.auto_map_schemas(source_meta, target_meta): сопоставление
      объектов по kind+имени/синониму, реквизитов по нормализованному имени;
      -> {ok, rules:[{source,target,attributes}], matched, unmatched}
- [x] ai_skills.explain_diff(diff): причины (только в источнике/приёмнике,
      изменение типа; 'Структуры совпадают.')
- [x] ai_skills.compress_metadata(meta, top_tables): {kinds, objects, top,
      total_attrs} — саммари для контекста LLM
- [x] MCP-тулы auto_map_schemas и explain_diff (JSON, ошибка -> {ok:False})
- [x] examples/autonomous_migration.md + context_compressor.md
- [x] Ворота: pytest (+7), conformance, ruff, mypy (51), check_bsl,
      vitest — зелёные; релиз 0.23.0
