# Proposal — фаза-47-0-30

**Goal:** Фаза 47 (0.30.0, финальная из раунда 4) — архитектурные хвосты: (1) errors.py OnecConverterError — единый предок; CloneError/SqlSourceError/HealthError наследуют (audit осознанно без доменной ошибки — валидация уровня ValueError, честное отклонение); (2) HttpClient83._ensure_token: лимит попыток OAuth2-токена за сессию (max_token_attempts, по умолчанию 5; блокированная попытка не инкрементирует); (3) cache.py потокобезопасность (RLock вокруг всех операций) + concurrent-тест 8 потоков; (4) read_metadata: понятная ошибка на битых файлах (FormatError с путём и причиной); (5) _blob_cache лимит 64 МБ с полным сбросом при переполнении; (6) секция Security в CHANGELOG; (7) тесты +6 в tests/test_phase47_arch.py. CHANGELOG 0.30.0 (итог фаз 41-47), план ✅, релиз.

- Platform: тесты в E:\test через gates.sh; версия 0.30.0; audit осознанно без OnecConverterError (валидация уровня — ValueError)
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b, фаза-32-0-15:forge:c7ae2cc67289, mcp-python-1-7:forge:cfc3bc6d2af5
