# Forge Report — фазу-22-безопасность-приёмника

- **Status:** complete
- **Done:** 10 · **Skipped (cache):** 0 · **Pending:** 0
- **Generated:** 2026-08-08T20:23:56.073Z

| Task | Status |
|------|--------|
| [fact] `jwt_auth.py`: HS256 mint/verify на stdlib (эталон для BSL) | done |
| [fact] `HttpClient83`: OAuth2 client-credentials (token_url/client_id/ | done |
| [fact] конфиг `[auth]` в onec.toml + флаги `load --token-url/--client-id/ | done |
| [fact] проверка Bearer-JWT: HMAC-SHA256 (ключ — секрет), exp, issuer; | done |
| [fact] check_bsl проходит (нет дублей, обработчики Экспорт) | done |
| [fact] jwt_auth: валидный → ok; истёкший/неверная подпись/чужой issuer/ | done |
| [fact] OAuth2 mock: Bearer-заголовок, кеш токена, refresh на 401, | done |
| [fact] gates-marker: BSL содержит ПроверитьJWT/HMACSHA256/issuer; | done |
| [fact] README + extension_83/README: раздел «Аутентификация приёмника | done |
| [assumption] релиз 0.5.0: TestPyPI → PyPI → GitHub Release | done |


