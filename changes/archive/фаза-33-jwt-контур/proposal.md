# Proposal — фаза-33-0-16

**Goal:** Фаза 33 (0.16.0) — JWT-контур целиком в onec-converter: (1) CLI подкоманда `mint-token --secret SECRET [--sub SUB] [--exp-min N]` на базе jwt_auth.mint_jwt() — выпускает HS256 JWT Bearer-токен на общем секрете (печать токена); (2) http_client: режим mint-token/secret для load --http --token-url? Пересмотреть — реально подключить mint_jwt к http_client как режим (если --secret задан без token_url, выпускать токен локально вместо client-credentials); (3) openapi BearerAuth уже документирован в Фазе 32; (4) extension_83/README + README: токен через mint-token (локальный, без OAuth2-сервера), token_url требует внешний сервер; (5) тест согласования mint_jwt -> ПроверитьJWT: питон выпускает токен, BSL-логика ПроверитьJWT (моделируется питоном по той же схеме HMAC) его принимает — эталонный вектор; (6) тесты CLI mint-token; (7) CHANGELOG 0.16.0, план Фаза 33 ✅, релиз 0.16.0.

- Platform: any
- Constraints: тесты в E:\test через gates.sh; версия 0.16.0; mypy только src; BSL в CP866
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9, mcp-python-1-7:forge:5ed7067daeab, mcp-python-1-7:forge:cfc3bc6d2af5
