# Design — фаза-11-новая-порция

## Цель

Пересмотреть блок-лист идей (docs/ideas.md, «Не взято и почему») и реализовать
2–3 идеи, ставшие применимыми после фаз 7–10. Авторский код, только stdlib,
реальные базы read-only, ворота pytest / mypy strict / ruff / vitest.

## Исследование (спайк, выполнено до дизайна)

На реальной базе 1C_8.3 (1Cv8.1CD) проверено:
- **PARAMS** — параметры (locale.inf, log.inf…), не история версий.
- **IBVERSION** — версия ИБ + требуемая версия платформы (закодированные числа).
- **CONFIG / CONFIGSAVE** — текущая и сохранённая конфигурация (файлы по именам
  GUID-узлов; в сумме 47 671 ключ). CONFIGSAVE = последнее сохранение
  конфигурации → дифф «текущая ↔ сохранённая» = практичная история.
- **`versions`** (3.6 МБ) — каталог всех файлов конфигурации
  `{1,47623,"",<file-guid>,<config-key>,…}` (не история версий).
- **`version`** — структура версии формата; **`siVersions`** — версии .si-файлов.
- **`read_dbnames()`** — 36 378 записей GUID → (kind, table_number): основа
  сравнения ИБ по GUID (стабильный идентификатор вместо имени).
- **`read_metadata()`** — объекты конфигурации с GUID/name/table.
- История версий конфигурации в смысле хранилища конфигуратора в файле базы
  ОТСУТСТВУЕТ — реализуем честный суррогат: версии платформы/ИБ/формата +
  дифф CONFIG↔CONFIGSAVE.

## Идеи (выбраны 3)

### E1 — Консоль запросов конфигурации (SQL-подобный язык)

`query.py`: `query_table_sql(db, table, select, where, order_by, limit)` —
безопасный лексический разбор (без exec):
- SELECT: `*` или список полей; REF-поля → `{"guid","name"}` через `ref_name()`;
- WHERE: `f=val; f2>10; name LIKE '…%'` (операторы =, !=, <, >, <=, >=, LIKE);
- ORDER BY `field ASC|DESC`, LIMIT.
Работает поверх `Database1CD.table_rows`. Синтаксис WHERE совместим с текущим
`query_table` (C3) — расширение, не ломка.
Интерфейсы: CLI `onec-converter query`, MCP-тул `query_sql`.

### E2 — Сравнение ИБ по GUID

`guid_diff.py`: `guid_diff(source_dir, target_dir)`:
- объекты конфигурации по GUID (`read_metadata`): только-в-источнике,
  только-в-приёмнике, общие с расхождением имени/типа;
- таблицы по GUID (`read_dbnames`): same — полнота переноса на уровне ссылок.
Отчёт — JSON (для MCP) / текст (CLI).
Интерфейсы: CLI `onec-converter guid-diff`, MCP-тул `guid_diff`.

### E3 — Версии конфигурации (формат / ИБ / платформа + дифф сохранений)

`config_versions.py`: `config_versions(path)`:
- формат файла (`db.version`), версия ИБ и требуемая платформа (IBVERSION);
- файлы конфигурации: число в CONFIG/CONFIGSAVE/PARAMS + даты CREATION/MODIFIED;
- дифф CONFIG↔CONFIGSAVE: добавлено / удалено / изменено (по размеру) — «что
  изменилось с последнего сохранения».
Интерфейсы: CLI `onec-converter config-versions`, MCP-тул `config_versions`.

## Документация

- `docs/ideas.md` — новый трек E (E1–E3) со статусами + обновление «Не взято»
  (история версий хранилища — вне файла базы; реализован CONFIG↔CONFIGSAVE-дифф).
- `docs/format-8x.md` — раздел «Версии и сохранения» (PARAMS/IBVERSION/CONFIG/
  CONFIGSAVE/versions/version — что лежит и как читать).
- `README.md` — раздел «Фаза 11» со статусами.

## Модули

- `src/onec_converter/query.py`
- `src/onec_converter/guid_diff.py`
- `src/onec_converter/config_versions.py`
- `src/onec_converter/cli.py` — 3 новые подкоманды
- `src/onec_converter/mcp_server.py` — 3 новых тула
- тесты: `tests/test_query.py`, `tests/test_guid_diff.py`,
  `tests/test_config_versions.py` (+ интеграционные, marker `integration`)

## Спека (drift)

`# Spec: фаза_11_идеи` → export `фаза_11_идеи` в `src/tasks/фаза_11_идеи.ts`.

## Ворота

pytest (все тесты, включая integration на реальных базах read-only),
mypy strict, ruff, vitest (сниппеты). Python 3.11+, Windows.
