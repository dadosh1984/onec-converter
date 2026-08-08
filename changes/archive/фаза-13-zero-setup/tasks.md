# Tasks — фаза-13-zero-setup

Прямая загрузка в 1CD без HTTP-расширения (вариант A zero-setup): transform →
load_direct → копия 1Cv8.1CD приёмника (write_8x, Фазы 10–12).

- [x] [spike] Контракт: объект после transform (type/key/attributes с русскими
      именами) → таблица приёмника (read_metadata: kind+name → _REFERENCE_n,
      field_map русское имя → физическое поле), _IDRREF 16 байт (префикс
      таблицы + уникальные 12) — зафиксировать в docs/pipeline.md
- [x] [fact] `load_8x.py`: `object_to_row(table_def, field_map, obj, idref)` —
      сборка строки по типам FieldDef (NVC/NC/N/L/DT/B/RV); unit-тесты
      на всех типах
- [x] [fact] `load_8x.py`: `load_direct(target_dir, objects, workdir)` — копия
      приёмника, группировка строк по таблицам, append_records, статистика;
      unit-тест на синтетической базе (create_1cd) → парсер читает
- [x] [assumption] CLI `onec-converter load --direct <target-dir> --input`
      (альтернатива --http) + MCP-тул `load_direct`; unit-тесты CLI
- [x] [fact] Интеграционный тест: transform e2e (7.7→8.3 правила, gen_dat) →
      load_direct в КОПИЮ реальной 1C_8.1 → парсер читает, verify (число
      строк == число объектов)
- [x] [assumption] Документация: docs/zero-setup.md (вариант A: MVP реализован,
      команда, ограничения), README («Прямая загрузка (Фаза 13)»),
      docs/pipeline.md (шаг load: файл/HTTP/прямая запись)

Ворота: pytest (вкл. integration), mypy strict, ruff, vitest (Orion shield).
Python 3.11+, Windows, реальные базы read-only (запись только в tmp-копии).
Только stdlib.
