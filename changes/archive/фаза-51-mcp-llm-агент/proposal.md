# Proposal — фаза-51-0-34

**Goal:** Фаза 51 (0.34.0) — MCP и LLM-агент (раунд 5): (1) MCP-тулы compress_metadata/audit_verify/cache_stats (U19/U20/U22), реестр 15->18; (2) таймаут _run_timeout на тяжёлые read-тулы через concurrent.futures (U21); (3) ONEC_MCP_ROLE=inspect блокирует migrate/load_direct и скрывает write-шаги из tools() (U23); (4) progress migrate в stderr — нет-оп (U24); (5) ai-map --objects фильтр (U25); (6) диалог дополнен (U26); commands-map MCP 18. Тесты +9 в tests/test_phase51_mcp_agent.py. CHANGELOG 0.34.0, план ✅, релиз.

- Platform: тесты в E:\tmp; версия 0.34.0; реестр MCP 15->18
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фаза-37-0-20:forge:f966453280f8, фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b, фаза-34-0-17:forge:7931121bac53
