# Proposal — фазу-22-безопасность-приёмника

**Goal:** Реализовать Фазу 22: безопасность приёмника OAuth2 + JWT для onec-converter. Клиент (http_client.py): поддержка OAuth2 client-credentials — получение токена с token_url и автоматический заголовок Authorization: Bearer, fallback на X-API-Key. Приёмник (extension_83/Module.bsl): проверка Bearer-JWT (подпись HMAC, срок жизни, issuer) вместо/дополнение shared-secret. Конфиг onec.toml: [auth] token_url/client_id/secret. Тесты: получение токена (mock), истёкший/неверный → 401, валидный → 200. Доки README. Ворота зелёные, релиз 0.5.0.

- Platform: any
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** mcp-python-1-7:forge:cfc3bc6d2af5, фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9, mcp-python-1-7:forge:5ed7067daeab, расширить-прямую-запись-1cd:shield:a4c1c5d3cb28
