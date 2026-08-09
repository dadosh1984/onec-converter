# Result — изучить-глубоко-внешнюю-обработку

- **Status:** INCOMPLETE
- **Tasks:** 21/21 done
**Guard:** lint:SKIP, type:FAIL, test:SKIP, drift:FAIL, yagni:SKIP, economy:PASS, security:PASS, policy:PASS, verifiability:WARN
- **Budget:** compact
- **Constraints:** compact
- **Generated:** 2026-08-09T16:59:09.302Z

## Checklist

- [x] Разобрать бинарный контейнер .epf (сигнатура, индекс, узлы, deflate-блоки) — `epf_extracted/`
- [x] Извлечь 22 внутренних файла (формы + модули), декодировать текстовые потоки 1С (BOM, `{1,{0,...`)
- [x] Извлечь исходный код модулей (главный модуль — 2946 строк) — `epf_extracted/modules/`
- [x] Составить схему алгоритма: 3 режима загрузки, маппинг колонок, типизация, поиск ссылок, запись — `design.md` §1–4
- [x] Изучить возможности onec_converter (чтение 1Cv8.1CD/1Cv7, запись 8.x на копиях, RefResolver, openpyxl)
- [x] Спроектировать архитектуру: модули bridge_format/typify/lookup/epf_load + доработка write_8x.update_record — `design.md` §5
- [x] Определить формат xlsx-моста (лист Настройки + лист Данные, маппинг C1–C11 совместим с макетом epf)
- [x] `bridge_format.py`: парсинг/запись xlsx-моста (шапка, маппинг C1–C11, подвал) — 9 тестов, ruff+mypy чисто
- [x] `typify.py`: текст → число/булево/дата/строка/ссылка («да/истина/включено»→1, даты ДД.ММ.ГГГГ ЧЧ:ММ:СС с авто-веком, квалификаторы) — 15 тестов
- [x] `lookup.py`: FieldLookupIndex (Код/Наименование/Номер/Дата/реквизит, нормализация значений) — 6 тестов
- [x] `write_8x.update_record` + `overwrite_row` (перезапись по _IDRREF/позиции) — 4 теста
- [x] `epf_load.py`: find-or-create для режимов 0 (справочник), 1 (табличная часть) и 2 (регистр), отмеченные колонки, значение по умолчанию (Сегодня()) — 6 тестов (в т.ч. режим ТЧ: владелец+дописывание строк в _VT)
- [x] События-хуки: hooks.py (before_write/after_write: module:func или sandbox-eval; «Вычислять» для колонок) — 5 тестов (test_hooks.py)
- [x] CLI `bridge-export` / `bridge-import` (+ восстановлен `export-xlsx`, реестр команд 33→37, docs/commands-map.md)
- [x] Сквозной тест: источник → xlsx-мост → копия приёмника → verify (test_bridge_e2e) — 3 теста
- [x] Приёмка на реальной базе 1C_8.1/1Cv8.1CD: export Справочник (_REFERENCE7) → мост → import в копию (2.54 ГБ) → updated=1, errors=0, оригинал не тронут (E:/test/bridge_smoke)
- [x] Lookup-расширение «документы Номер от Дата»: resolve_day — поиск по календарному дню (test_lookup, 1 тест; test_hooks) + 5 тестов хуков
- [x] Lookup-расширение «СвязьПоВладельцу»: resolve(owner=...) с фильтром по _OWNERIDRREF (подчинённые/иерархические справочники) + _find_catalog применяет владельца при owner_ref. Тест test_resolve_filters_by_owner.
- [x] Перечисление — осознанно отложено/вне области: таблица `_Enum<N>` несёт только `_IDRREF`+`_ENUMORDER`, синоним элемента лежит в CONFIG; сопоставление представления->ссылка требует парсинга CONFIG (отдельная задача; сценарий без связи по синониму — в typify `Перечисление.X` уже как ссылочный тип). Ведётся в ОСТАВШИЕСЯ_ЭТАПЫ.md и в change «изучить-типовую-обработку-1с»
- [x] Обратный контроль переноса: bridge_verify.py + CLI `bridge-verify` — выгрузка из КОПИИ приёмника в мост и сверка всех колонок с исходным (matched/mismatched/missing/extra). Команда, реестр 37→38, E2E-тест. Сверено на реальной базе 1C_8.1: ok=True, matched=1, diffs=0. — по идее: «быть 100% уверенным»
- [x] Ускорение тестов: 183с → 27с. pytest.ini `addopts=-m "not integration"` (по умолчанию исключены тяжёлые real-base тесты); пометил integration `test_extract_8x_named_types_real_base` (64с). Real-базы — по `-m integration`. Также исправлены пред-существующие ruff-ошибки (RUF015) и реестр CLI 37→38

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | FAIL | Command failed: npm exec tsc --noEmit
npm warn Unknown cli config "--noEmit". This will stop working in the next major version of npm.
 |
| test | SKIP | no test script in package.json |
| drift | FAIL | invalid capability name(s): 1_1cv8_1cd_1cv7_dbf_epf_e_test — "# Spec:" headings must be valid JS identifiers matching an export in src/tasks (rename the heading to the exported module's name, e.g. "# Spec: core" for src/tasks/core.ts) |
| yagni | SKIP | no existing .ts sources to build a baseline from |
| economy | PASS | cache 222.8 KB of 100.0 MB (873 entries) — within budget; ≈ 780742 tok saved across 484 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | WARN | oracles: none · verifiability level 0 · tests weak/missing — low verifiability: treat this PASS as lower-confidence (human review advised) |

## Artifacts

- `changes/изучить-глубоко-внешнюю-обработку/proposal.md`
- `changes/изучить-глубоко-внешнюю-обработку/design.md`
- `changes/изучить-глубоко-внешнюю-обработку/tasks.md`
- `reports/изучить-глубоко-внешнюю-обработку/guard-report.md`
- `changes/изучить-глубоко-внешнюю-обработку/specs/1_1cv8_1cd_1cv7_dbf_epf_e_test/spec.md`
- `changes/изучить-глубоко-внешнюю-обработку/snippets/`

## Next steps

Run `orion shield изучить-глубоко-внешнюю-обработку` to get a guard verdict.
