# Tasks — расширение прямой записи на ссылки и табличные части (Фаза 15)

Ворота: mypy strict, ruff, pytest, vitest. Запись только на копиях.
Ограничение Фазы 14 (индексы не пересобираются) учитываем и документируем.

## Spike (документация формата)
- [x] [spike] docs/format-8x.md: раздел «Ссылки и табличные части (Фаза 15)» —
      REF-поля (B16 `_FLD...RREF`, пустой=нули), документ-база `_DOCUMENTN`
      (`_DATE_TIME/_NUMBERPREFIX/_NUMBER/_POSTED`), VT-таблица `_<Base>_VT<num>`
      (`_<Base>IDRREF`, `_KEYFIELD`, `_LINENO<num>`), индексы VT не пересобираются

## RED — тесты на нереализованном
- [x] [fact] tests/test_load_8x_refs.py: `test_ref_field_written` — синтетика:
      REF-поле заполняется `_IDRREF` приёмника по ключу — FAIL до кода
- [x] [fact] `test_missing_ref_zeros_and_reported` — ненайденный ref → 16 нулей
      + запись в отчёт (не прерывает пакет) — FAIL
- [x] [fact] `test_vt_rows_written_with_parent` — табличная часть: базовая
      строка + `_VT`-строки c `_<Base>IDRREF`=idref базы и `LINENO` — FAIL
- [x] [fact] `test_doc_number_date_posted` — `_NUMBER` из key, `_DATE_TIME`/
      `_POSTED` из атрибутов или нули — FAIL

## GREEN — реализация в load_8x.py (+ helper в source_8x_file при необходимости)
- [x] [fact] индекс `(таблица приёмника, ключ) → _IDRREF` из существующих строк
      (по `_CODE`/`_DESCRIPTION`/ключу объекта)
- [x] [fact] `_resolve_ref(meta, references, index)` → 16 байт `_IDRREF` приёмника
      или нули + отчёт; значение `"Тип:ключ|ключ2"`, тип через read_dbnames
- [x] [fact] REF-запись в `object_to_row`: для полей `type=='ref'` заполнить
      из references → 16 байт; `_PARENTIDRREF`/<Base>IDRREF — parent
- [x] [fact] VT-запись: из объектов `ТабличнаяЧасть.X` — строка в `_VT`-таблицу
      (parent-idref + `_LINENO` + реквизиты)
- [x] [fact] документ-база: `_NUMBER` из key[0]/атрибута, `_DATE_TIME`/`_POSTED`/
      `_NUMBERPREFIX` из атрибутов или нули
- [x] [fact] отчёт `load_direct`: ключ `ref_warnings`/`errors` для ненайденных REF

## GREEN — интеграционный e2e на копии 8.1
- [x] [fact] tests/test_load_8x_doc_e2e.py: на КОПИИ 8.1 — документ со ссылкой
      и табличной частью (например `_DOCUMENT41`/`_DOCUMENT41_VT770`-подобный
      синтетический документ) → парсер читает базовые + VT-строки, parent связь
      верна; оригинал не изменён

## Постусловия / верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] README — снять ограничения MVP «ссылки/ТЧ»; оставить
      ограничение по индексам VT (Фаза 14)
