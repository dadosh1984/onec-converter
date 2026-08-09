# Spec: core

## Purpose
Продукт и документация: tamper-evident раздел README, feature matrix,
пример LLM-диалога, документирование безопасности расширения,
реальная диагностика base_health, экранирование telegram_url,
прогресс clone_db, рецепт полного цикла. Версия 0.29.0.

## Acceptance criteria
- [x] README: «Tamper-evident audit log» (цепочка SHA-256, verify_audit +
      --cross-files, ссылка на рецепт) и feature matrix (7.7/файл 8.x/SQL 8.x)
- [x] examples/llm_agent_dialog.md: диалог с auto_map_schemas/explain_diff,
      упоминается confidence
- [x] extension_83/README: Совпадает() (constant-time), rate-limit
      (5 неудач) с честным ограничением (переменные модуля HTTP-сервиса)
- [x] base_health.errors — реальная диагностика: пустой файл, блокировки
      (1Cv8.1CL и др.)
- [x] notify.telegram_url экранирует token/chat_id (urllib.parse.quote)
- [x] clone_db: WorkflowProgress(log/total); прогресс-логи в stderr —
      stdout остаётся машиночитаемым (JSON CLI-тест не сломан)
- [x] docs/recipes/полный-цикл-clone-load-verify-audit.md (7 шагов)
- [x] Ворота: pytest (+6), conformance, ruff, mypy, check_bsl, vitest —
      зелёные; релиз 0.29.0
