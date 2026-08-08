# Design — фаза-13-zero-setup

## Цель

Вариант A из `docs/zero-setup.md`: загрузка в приёмник 8.x БЕЗ HTTP-расширения —
напрямую в копию `1Cv8.1CD` через готовый writer (Фазы 10–12). Пользователь,
не знающий 1С, не собирает и не подключает расширение.

## Контракт (проверено на коде)

- После `transform` объект: `{'type': 'Справочник.X', 'key': [...],
  'attributes': {имя_реквизита_приёмника: значение}, 'references': {...}}`
  (атрибуты — русские имена, как в `read_metadata` → `attributes[].name`).
- `read_metadata(target)` → объекты с `kind/name/table/ref_num/attributes`
  (физическое поле + тип + длина). `_SYSTEM_FIELDS` маппит `_CODE`→Код и т.п.
- Таблица приёмника: `{kind}.{name}` → `table` (`_REFERENCE_n`).
- Поля строки: `_VERSION` (RV 16), `_IDRREF` (B 16), `_MARKED` (L), `_CODE`,
  `_DESCRIPTION`, атрибуты.
- `_IDRREF` реальной базы (8.1): 16 байт, первые 4 — «префикс таблицы»
  (у всех строк таблицы одинаковый), последние 12 — уникальные.
  MVP: префикс из первой непустой строки таблицы (или нули), уникальные
  12 байт — счётчик/рандом; наш парсер читает без потерь, 1С —
  последовательным сканом (точная семантика префикса не гарантируется —
  фиксируем ограничение).

## Изменения

### `src/onec_converter/load_8x.py`

- `object_to_row(table_def, field_map, obj, idref) -> bytes` — сборка строки
  по типам FieldDef (NVC/NC/N/L/DT/B/RV), кодирование как в fake_1cd
  (enc_nvc/enc_nc/enc_numeric/enc_datetime), `_CODE`/`_DESCRIPTION` из
  `key`/атрибутов, атрибуты по field_map (русское имя → физическое поле).
- `_idref_prefix(db, table_name) -> bytes` — первые 4 байта из первой
  непустой строки (или b'\x00'*4).
- `load_direct(target_dir, objects, workdir) -> dict`:
  - копия приёмника `copy_1cd(target_dir/1Cv8.1CD → workdir/1Cv8.1CD)`;
  - для каждого объекта: таблица через read_metadata; строки группируются
    по таблицам; append_records(копия, table, rows) — LockError/WriteError
    наружу; статистика {table: n, total, copy_path};
  - оригинал никогда не изменяется.

### CLI / MCP

- `onec-converter load --direct <target-dir> --input <batch.json>`
  (альтернатива `--http`); JSON-ответ {ok, copy_path, total, tables}.
- MCP-тул `load_direct(target_dir, input_file, workdir)` — тот же контракт,
  что HTTP-load (после transform).

### Тесты

- `tests/test_load_8x.py` (unit): object_to_row (все типы полей через
  синтетический FieldDef), _IDRREF уникальность, load_direct на
  синтетической базе (create_1cd с таблицей приёмника) → парсер читает.
- `tests/test_load_8x_e2e.py` (integration): transform e2e (7.7→8.3 правила,
  gen_dat) → load_direct в копию реальной `1C_8.1` → парсер читает,
  verify: число строк == число объектов.

### Документация

- `docs/zero-setup.md` — вариант A: статус «MVP реализован (Фаза 13)»,
  команда и ограничения (_IDRREF, индексы).
- `README.md` — раздел «Zero-setup: прямая загрузка (Фаза 13)».
- `docs/pipeline.md` — шаг load: файл/HTTP/прямая запись.

## Спека (drift)

`# Spec: load_direct` → export `load_direct` в `src/tasks/load_direct.ts`.

## Ворота

pytest (вкл. integration), mypy strict, ruff, vitest. Python 3.11+,
Windows, реальные базы read-only (запись — только tmp-копии).
