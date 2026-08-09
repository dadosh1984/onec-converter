# Дизайн — Фаза 54 (0.37.0): дефекты и чистка

По аудиту раунда 6 (docs/audit-round-6d.md). Реализовано подтверждённое,
без переусердствования — только то, что не рискует сломать проект.

## Сделано
- A1: `ai_skills.auto_map_schemas` — убран мёртвый код (`src_attrs`/`del`).
- B5: единый декодер `cli._table_row_to_rec` — убрано дублирование
  dump-records/export-xlsx.
- B6: константа `config.DEFAULT_SOURCE_ENCODING` (cp866), применена в cli.
- A2: `config.load` — strip() строковых значений.
- A5: `cmd_load` без target/http/direct — явная ошибка.
- A7: `audit --csv-out` — экранирование формул Excel (A7/E2).
- A3/A8: зафиксирован контракт stdout=данные / stderr=метаданные в
  audit --json и sonar-report (документация в docstring).
- H-фикс: `test_cli_entrypoint` устойчив к cp1251-консолям (PYTHONIOENCODING).
- openapi.yaml перегенерирован на 0.37.0 (вер цание единого источника).

## Сознательно НЕ делал (баланс «не переусердствовать»)
- A4 — не баг: verify-фильтр корректно обрабатывает `Таблица.*`.
- A6 — не проблема: `_notify` вызывается только из load.

## Верификация
- ruff: src+tests clean; mypy: 54 файла clean.
- pytest: 517 старых +5 новых green (включая conformance 5).
- vitest: 355 green.
- Бенчмарк-ворота без деградации (изменения не касаются hot-path).
