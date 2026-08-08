# Spec: core

## Purpose
Фаза 18 — безопасность и качество данных: закрыть найденные анализами дыры
анонимизации, HTTP-приёмника, кеша и добавить строгую валидацию.

## Requirements
- [REQ-1] anonymizer: маскировать 2-словные ФИО и любой регистр; HMAC-SHA256
  для режима 'hash' (env ONEC_HASH_SECRET / параметр secret); профили 152-ФЗ.
- [REQ-2] http_client: ретрай 5xx с backoff, 4xx без ретрая; осмысленная
  ошибка с кодом+телом; опция `api_key` → заголовок X-API-Key.
- [REQ-3] Cache: санитизация ключей/имён (запрет `..`/`/`); методов `stats()`;
  CLI `onec-converter cache stats|clear`.
- [REQ-4] Module.bsl: аутентификация (X-API-Key, 401); транзакция +
  Попытка/Исключение на объект (частичный errors); валидация реквизитов.
- [REQ-5] Strict Mode: `src/onec_converter/strict.py` (validate_value/
  validate_object) + `load_direct(..., strict=True)` → LoadError при дефекте.
- [REQ-6] Ворота: pytest, ruff, mypy strict, vitest; обратная совместимость.
