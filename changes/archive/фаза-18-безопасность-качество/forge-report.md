# Forge Report — фаза-18-безопасность-качество

- **Status:** complete
- **Done:** 15 · **Skipped (cache):** 0 · **Pending:** 0
- **Generated:** 2026-08-08T17:26:43.861Z

| Task | Status |
|------|--------|
| [fact] `_FIO_RE`: маскировать «Фамилия Имя» (2 слова) и любой регистр | done |
| [fact] `_hash_token`: HMAC-SHA256 с ключом (env `ONEC_HASH_SECRET` / параметр | done |
| [fact] профили 152-ФЗ: `PII_PROFILES` = salary/retail/medical (готовые поля) | done |
| [fact] тесты: 2-словные/регистр ФИО, стабильность+зависимость HMAC, warning | done |
| [fact] `_request`: ретрай 5xx с backoff; 4xx — без retry (осмысленно); | done |
| [fact] тесты: 5xx ретраится, 4xx нет, transport-ошибка ретраится, | done |
| [fact] санитизация ключей/имён (запрет `..`/`/`/`\`), разрешить `.` у файлов | done |
| [fact] `Cache.stats()` (число файлов/размер) + CLI `onec-converter cache stats|clear` | done |
| [fact] тесты: path-traversal отвергается, имя с точкой ок, stats верны | done |
| [fact] аутентификация: заголовок X-API-Key (401 при несовпадении) — обе ф-ции | done |
| [fact] транзакция + Попытка/Исключение на каждый объект (частичный errors), | done |
| [fact] `src/onec_converter/strict.py`: validate_value/validate_object | done |
| [fact] `load_direct(..., strict=False)`: при strict=True → LoadError с деталями | done |
| [fact] тесты: строка/число/дата/ref валидация, объект с ошибками, показ | done |
| [assumption] docs/development-plan.md: Фаза 18 отмечена выполненной | done |


