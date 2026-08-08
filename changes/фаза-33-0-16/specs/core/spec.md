# Spec: core

## Purpose
Замкнуть JWT-контур: локальная выдача токенов (mint-token), подключение
её к http_client и форме load, документирование трёх режимов аутентификации.
Версия 0.16.0.

## Acceptance criteria
- [x] CLI `mint-token --secret [--issuer onec-converter --exp-min 60]` —
      печатает HS256 JWT на общем секрете; возвращает 0
- [x] http_client: при заданном secret (без token_url) _ensure_token
      выпускает локальный JWT через mint_jwt и шлёт Authorization: Bearer
- [x] load --http --secret: локальный mint-token (конфиг [auth] secret)
- [x] extension_83/README + README: три режима (X-API-Key, OAuth2 token_url,
      локальный mint-token / --secret)
- [x] тест: mint_jwt ↔ BSL-логика ПроверитьJWT (base64url + alg=HS256 +
      exp/iss + HMAC-SHA256 подпись на общем секрете)
- [x] openapi: BearerAuth зарегистрирован (Фаза 32)
- [x] Ворота: pytest (+6), conformance, ruff, mypy (43), vitest — зелёные;
      релиз 0.16.0
