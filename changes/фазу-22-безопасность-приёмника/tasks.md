# Tasks — Фаза 22: безопасность приёмника (OAuth2 + JWT)

Ворота: mypy strict, ruff, pytest, vitest, check_bsl. Релиз 0.5.0.

## Клиент (Python)
- [x] [fact] `jwt_auth.py`: HS256 mint/verify на stdlib (эталон для BSL)
- [x] [fact] `HttpClient83`: OAuth2 client-credentials (token_url/client_id/
      client_secret) — Bearer-заголовок, кеш токена, refresh при 401,
      fallback на X-API-Key
- [x] [fact] конфиг `[auth]` в onec.toml + флаги `load --token-url/--client-id/
      --client-secret`

## Приёмник (Module.bsl)
- [x] [fact] проверка Bearer-JWT: HMAC-SHA256 (ключ — секрет), exp, issuer;
      ключ ИЛИ токен → 401 при невалидном
- [x] [fact] check_bsl проходит (нет дублей, обработчики Экспорт)

## Тесты
- [x] [fact] jwt_auth: валидный → ok; истёкший/неверная подпись/чужой issuer/
      битый payload → отклонён
- [x] [fact] OAuth2 mock: Bearer-заголовок, кеш токена, refresh на 401,
      fallback X-API-Key, ошибка token-endpoint
- [x] [fact] gates-marker: BSL содержит ПроверитьJWT/HMACSHA256/issuer;
      конфиг [auth] читается

## Доки
- [x] [fact] README + extension_83/README: раздел «Аутентификация приёмника
      (OAuth2/JWT)»; CHANGELOG 0.5.0; план — Фаза 22 ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.5.0: TestPyPI → PyPI → GitHub Release
