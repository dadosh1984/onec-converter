# research/xlsx-bridge — перенос в onec_converter

Справочные данные xlsx-моста (ранее в отдельной папке `1c-transfer-xlsx`),
перенесены в основной проект `onec_converter` 2026-08-09.

## Состав
- `epf_extracted/` — распакованный контейнер `Выгрузка и загрузка данных XML.epf`
  (скобкофайлы + модули на BSL). Обработка — на деле **xlsx-мост** (работа через
  Excel), не XML-формат 1С.
- `epf_extracted_xml/` — пусто (на момент переноса).
- `Выгрузка и загрузка данных XML.epf` / `ЗагрузкаДанныхИзТабличногоДокумента_УФ_v2.epf` —
  исходные внешние обработки.
- `ОСТАВШИЕСЯ_ЭТАПЫ.md` — сводка незакрытых этапов ядра переноса.

## Код моста (живёт в src/onec_converter)
- `bridge_format.py`, `typify.py`, `lookup.py`, `hooks.py`, `epf_load.py`,
  `bridge_export.py`, `bridge_verify.py`, `enum_mapper.py` (TOON),
  `enum_resolver.py` (перечисления, Фаза 3 п.1.3).
- Тесты: `tests/test_bridge_*.py`, `tests/test_enum_resolver.py`, `tests/test_hooks.py`.

## orion-change
- Активный: `changes/изучить-типовую-обработку-1с` (7/7, spec `enum_xlsx_bridge`),
  capability-модуль `src/tasks/enum_xlsx_bridge.ts`.
- Архив: `changes/archive/изучить-глубоко-внешнюю-обработку`.
