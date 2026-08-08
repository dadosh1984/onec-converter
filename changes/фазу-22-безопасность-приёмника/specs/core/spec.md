# Spec: core

## Purpose
Реализовать Фазу 22: безопасность приёмника OAuth2 + JWT для onec-converter. Клиент (http_client.py): поддержка OAuth2 client-credentials — получение токена с token_url и автоматический заголовок Authorization: Bearer, fallback на X-API-Key. Приёмник (extension_83/Module.bsl): проверка Bearer-JWT (подпись HMAC, срок жизни, issuer) вместо/дополнение shared-secret. Конфиг onec.toml: [auth] token_url/client_id/secret. Тесты: получение токена (mock), истёкший/неверный → 401, валидный → 200. Доки README. Ворота зелёные, релиз 0.5.0.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
