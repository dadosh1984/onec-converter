# Spec: core

## Purpose
Архитектурные хвосты раунда 4 (финал): базовый класс ошибок, лимит
OAuth2-попыток, потокобезопасность кеша, понятные ошибки чтения,
лимит blob-кеша, секция Security. Версия 0.30.0.

## Acceptance criteria
- [x] errors.OnecConverterError; CloneError/SqlSourceError/HealthError
      наследуют (audit без доменной ошибки — валидация уровня остаётся
      ValueError; честное отклонение от черновика)
- [x] _ensure_token: max_token_attempts (5), блокированная попытка не
      инкрементирует счётчик; сообщение «лимит попыток»
- [x] Cache: RLock вокруг всех операций (put/get/has/get_json/stats/trim/
      drop/clear); concurrent-тест 8 потоков без ошибок
- [x] read_metadata: FormatError с путём и причиной на битых файлах
- [x] _blob_cache: лимит 64 МБ, полный сброс при переполнении
- [x] CHANGELOG: секция Security (rate-limit, constant-time, tamper-evident,
      анти-инъекция, OAuth2-лимит) + итог фаз 41-47
- [x] Ворота: pytest (+6), conformance, ruff, mypy (56), check_bsl, vitest —
      зелёные; релиз 0.30.0
