# Tasks — Фаза 33: JWT-контур целиком (0.16.0)

## CLI / http_client
- [x] [fact] CLI mint-token (--secret/--issuer/--exp-min); тест
- [x] [fact] http_client secret-режим (локальный mint-token, Bearer без
      X-API-Key); тест прохождения токена

## Доки и согласование
- [x] [fact] extension_83/README + README: три режима аутентификации
- [x] [fact] тест согласования mint_jwt ↔ ПроверитьJWT (эталонный вектор)
- [x] [fact] openapi bearerAuth (уже в Фазе 32)

## Доки / релиз
- [x] [fact] CHANGELOG 0.16.0; план Фаза 33 ✅
- [x] [assumption] ворота зелёные; релиз 0.16.0
