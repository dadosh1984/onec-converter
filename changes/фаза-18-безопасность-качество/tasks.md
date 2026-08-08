# Tasks — Фаза 18: безопасность и качество данных

Ворота: mypy strict, ruff, pytest, vitest. Авторский код; обратная совместимость.

## anonymizer (утечки ПДн)
- [x] [fact] `_FIO_RE`: маскировать «Фамилия Имя» (2 слова) и любой регистр
      («иванов иван иванович»); не трогать однобуквенные слова («Товар А»)
- [x] [fact] `_hash_token`: HMAC-SHA256 с ключом (env `ONEC_HASH_SECRET` / параметр
      secret); без ключа — предупреждение + фиксированная соль (не тихий sha256)
- [x] [fact] профили 152-ФЗ: `PII_PROFILES` = salary/retail/medical (готовые поля)
- [x] [fact] тесты: 2-словные/регистр ФИО, стабильность+зависимость HMAC, warning

## http_client (retry/ошибки)
- [x] [fact] `_request`: ретрай 5xx с backoff; 4xx — без retry (осмысленно);
      final-ошибка с кодом+телом; опция `api_key` → заголовок X-API-Key
- [x] [fact] тесты: 5xx ретраится, 4xx нет, transport-ошибка ретраится,
      осмысленные сообщения

## Cache (безопасность/лимиты)
- [x] [fact] санитизация ключей/имён (запрет `..`/`/`/`\`), разрешить `.` у файлов
- [x] [fact] `Cache.stats()` (число файлов/размер) + CLI `onec-converter cache stats|clear`
- [x] [fact] тесты: path-traversal отвергается, имя с точкой ок, stats верны

## Module.bsl (HTTP-приёмник)
- [x] [fact] аутентификация: заголовок X-API-Key (401 при несовпадении) — обе ф-ции
- [x] [fact] транзакция + Попытка/Исключение на каждый объект (частичный errors),
      валидация существования реквизита (антиинъекция)

## Strict Mode
- [x] [fact] `src/onec_converter/strict.py`: validate_value/validate_object
      (длины NVC/NC, диапазоны чисел, даты YYYYMMDDHHMMSS, REF 16 байт/GUID)
- [x] [fact] `load_direct(..., strict=False)`: при strict=True → LoadError с деталями
- [x] [fact] тесты: строка/число/дата/ref валидация, объект с ошибками, показ

## Верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] docs/development-plan.md: Фаза 18 отмечена выполненной
