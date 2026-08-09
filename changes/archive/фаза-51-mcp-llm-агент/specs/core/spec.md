# Spec: core

## Purpose
Усилить MCP-сервер для агентного использования: добавить «дорогие» read-тулы
(сжатие метаданных, комплаенс, кеш), защиту read-only роли, жёсткие таймауты
и CLI-фильтр автомаппинга. Версия 0.34.0.

## Acceptance criteria
- [x] MCP-тулы compress_metadata/audit_verify/cache_stats (U19/U20/U22);
      реестр MCP 15 -> 18
- [x] _run_timeout: твёрдый таймаут на тяжёлые read-тулы (U21) через
      concurrent.futures (не asyncio.run+to_thread — ждал join экзекьютора)
- [x] ONEC_MCP_ROLE=inspect: migrate/load_direct блокируются; write-шаги
      плейбука (init/extract/map/transform/load/preview) скрыты из tools() (U23)
- [x] migrate-прогресс в stderr (playbook_step/log) — проверено (U24, нет-оп)
- [x] ai-map --objects фильтр правил по типам (U25)
- [x] examples/llm_agent_dialog.md дополнен (новые тулы + inspect) (U26)
- [x] commands-map.md: MCP 18 тулов
- [x] ruff/mypy/pytest/conformance зелёные; релиз 0.34.0
