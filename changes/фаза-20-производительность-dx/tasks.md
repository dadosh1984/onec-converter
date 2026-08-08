# Tasks — Фаза 20: производительность и DX

Ворота: mypy strict, ruff, pytest, vitest. Авторский код.

## Потоковый extract (большие базы без OOM)
- [x] [fact] intermediate: `save_json_stream` (NDJSON-массив) + `load_json_stream`
      (генератор) — обратная совместимость с load_json_batch; тест
- [x] [fact] step_extract(stream=True): потоковая запись в файл, не держит все
      объекты в памяти

## dump-records
- [x] [fact] cli: подкоманда `dump-records --source-dir --table --limit --format
      (json|csv)` — вывод первых N строк таблицы; тест

## Конфиг-файл
- [x] [fact] `src/onec_converter/config.py`: читает onec.toml (source_encoding,
      limit, retries, rules_file, target_url, tmp_dir); дефолты при отсутствии
- [x] [fact] cmd_extract использует конфиг для source_encoding/limit; тест

## CHANGELOG
- [x] [fact] CHANGELOG.md пользовательским языком (возможности, безопасность,
      DX, ограничения)

## Верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] docs/development-plan.md: Фаза 20 отмечена выполненной
