# Задачи — Фаза 54 (0.37.0): дефекты и чистка

- [x] A1: убрать мёртвый код в ai_skills.auto_map_schemas
- [x] B5: вынести _table_row_to_rec (dump-records + export-xlsx)
- [x] B6: константа DEFAULT_SOURCE_ENCODING вместо хардкода cp866
- [x] A2: config.load strip() строковых значений + тест
- [x] A5: cmd_load без target/http/direct — ошибка + тест
- [x] A7: audit --csv-out экранирование формул Excel + тест
- [x] A3/A8: контракт потоков stdout/stderr (док в docstring)
- [x] H-фикс: test_cli_entrypoint устойчив к cp1251-консолям
- [x] версия 0.37.0, openapi.yaml перегенерирован, CHANGELOG
- [x] ворота green: ruff/mypy/pytest(522)/conformance/vitest(355)
