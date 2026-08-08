# Tasks — Фаза 31: качество и DX

Ворота: mypy strict, ruff, pytest, vitest; тесты в E:\test. Релиз 0.4.0.

## Cache — TTL/лимит (LRU)
- [x] [fact] `Cache.trim(max_bytes, ttl_seconds)`: эвикция — удаляет старше ttl,
      при превышении max_bytes — самые старые; `stats()` показывает возраст
- [x] [fact] тесты: trim по ttl, по max_bytes (удаляет старые, свежие целы)

## anonymizer — fuzz-тест
- [x] [fact] `tests/test_anonymizer_fuzz.py`: собственный генератор случайных
      строк — mask_fio не меняет их; обычные фразы («ООО Ромашка Плюс»,
      «красный диван») не портятся; mode='mask' без fields не укорачивает

## Module.bsl — нормализация replace
- [x] [fact] `НайтиОбъект2`: `СокрЛП` ключа/наименования перед поиском (не
      дубли из-за пробелов/регистра)

## Документация
- [x] [fact] extension_83/README.md: аутентификация (ОжидаемыйКлюч, X-API-Key,
      401) + пример --api-key/onec.toml; README: пример load --api-key
- [x] [fact] CHANGELOG: раздел 0.4.0; docs/implementation-plan.md: Фаза 31 ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.4.0: TestPyPI → PyPI → GitHub Release
