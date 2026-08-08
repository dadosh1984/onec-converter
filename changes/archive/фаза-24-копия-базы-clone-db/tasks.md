# Tasks — Фаза 24: Полный сценарий копии базы (clone-db + rollback)

Ворота: mypy strict, ruff, pytest, vitest. Релиз 0.9.0.

## clone-db
- [x] [fact] модуль clone_db.py: clone_db() — полная побитовая копия
      1Cv8.1CD, оригинал не тронут
- [x] [fact] кеш-сброс: Cache.drop по новому ключу после копии
- [x] [fact] --with-rules: файл правил → target/rules/ (стенд)
- [x] [fact] ошибки: нет 1Cv8.1CD / клонирование в себя → CloneError
- [x] [fact] CLI подкоманда clone-db (--source-dir --target-dir --with-rules)

## Снапшот / rollback
- [x] [fact] load_8x.load_direct: snapshot=True → workdir/snapshot.1CD
      до записи, возврат 'snapshot'
- [x] [fact] --no-snapshot (CLI load) и no_snapshot (MCP load_direct)
      отключают снапшот
- [x] [fact] тесты: snapshot создан == оригинал; restore при сбое
      (повреждённый copy_path ← снапшот); no-snapshot → snapshot=None

## Тесты и доки
- [x] [fact] тесты clone-db на синтетике: побитовая копия, tables, rules,
      ошибки, CLI; Cache.drop (кл1 удалён, кл2 цел)
- [x] [fact] docs/recipes: шаг «стенд через clone-db»
- [x] [fact] README: clone-db + snapshot в CLI-разделе
- [x] [fact] CHANGELOG 0.9.0, версия, план — Фаза 24 ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.9.0: TestPyPI → PyPI → GitHub Release
