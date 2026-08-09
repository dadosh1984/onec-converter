# Tasks — Фаза 47: архитектурные хвосты (0.30.0)

## Ошибки
- [x] [fact] OnecConverterError базовый класс (clone/sql/health наследуют)

## Сеть
- [x] [fact] лимит попыток OAuth2 в _ensure_token

## Кеш и чтение
- [x] [fact] потокобезопасность cache.py (RLock) + concurrent-тест
- [x] [fact] понятная ошибка read_metadata на битых файлах
- [x] [fact] эвикция/лимит _blob_cache

## Релиз
- [x] [fact] секция Security в CHANGELOG
- [x] [assumption] ворота зелёные; релиз 0.30.0
