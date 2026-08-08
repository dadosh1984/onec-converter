# Spec: core

## Purpose
Фаза 20 — производительность и DX: потоковый extract для больших баз,
команда dump-records, конфиг-файл onec.toml, CHANGELOG.

## Requirements
- [REQ-1] Потоковая сериализация intermediate (save_json_stream/load_json_stream),
  обратная совместимость с json-массивом; step_extract(stream=True) без OOM.
- [REQ-2] CLI `dump-records --source-dir --table --limit --format json|csv`.
- [REQ-3] Конфиг-файл onec.toml (source_encoding, limit, retries, ...), читается
  cmd_extract при отсутствии явных флагов.
- [REQ-4] CHANGELOG.md пользовательским языком.
- [REQ-5] Ворота зелёные: pytest, ruff, mypy strict, vitest.
