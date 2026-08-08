# Tasks — Фаза 32: Дефекты по итогам анализа (0.15.0)

## clone_db / cache
- [x] [fact] clone_db: file_key(dst) ДО copy2, дроп старого ключа; тест
- [x] [fact] cache: тест TTL-эвикции (get/has не возвращают stale)

## health
- [x] [fact] base_health: include_rows=False, sample_tables=N; тесты

## CI
- [x] [fact] check_bsl в gates.sh (цель bsl + all)

## audit / notify
- [x] [fact] audit: один handle + flush + ротация; тесты
- [x] [fact] notify: retry с backoff; тесты

## openapi / extract / BSL
- [x] [fact] openapi BearerAuth + тест соответствия путям
- [x] [fact] CLI extract → save_json_stream; тест
- [x] [fact] Module.bsl Совпадает (constant-time X-API-Key)

## Доки и релиз
- [x] [fact] CHANGELOG 0.15.0; план Фаза 32 ✅
- [x] [assumption] ворота зелёные; релиз 0.15.0
