# Result — 1-8-x-1cv8

- **Status:** SUCCESS
- **Tasks:** 13/13 done
**Guard:** lint:SKIP, type:PASS, test:PASS, drift:PASS, yagni:PASS, economy:PASS, security:PASS, policy:PASS, verifiability:PASS
- **Budget:** Фаза 5: парсер 1CD + status-тул + интеграционные тесты
- **Constraints:** Фаза 5: парсер 1CD + status-тул + интеграционные тесты
- **Generated:** 2026-08-08T12:29:24.292Z

## Checklist

- [x] [spike] Поток описаний таблиц в root-объекте 1CD: структура записей (имя, num, поля, DBSCHEMA-блок, first_block, chains); цепочки блоков FAT level 0/1; зафиксировать в `docs/format-8x.md`
- [x] [spike] Blob-цепочки (чанки 256 байт): адресация, размер, чтение; пример — таблица DBSCHEMA (SERIALIZEDDATA 449 КБ); зафиксировать в `docs/format-8x.md`
- [x] [spike] Конфигурация 8.1-эпохи: root `['2', <main_guid>, <base64>]` + GUID-файлы (zlib inflate); имена/синонимы объектов; привязка коллекции → таблица по порядку DBSCHEMA; зафиксировать в `docs/format-8x.md`
- [x] [fact] `source_8x_file`: парсер root-объекта → каталог таблиц (имена в обоих стилях `_REFERENCE3`/`_Reference74`, поля, first_block); unit-тест на синтетическом `.1CD`
- [x] [fact] `source_8x_file`: чтение строк таблиц по цепочкам блоков + декодирование полей (NVC=utf-16le с префиксом длины, RV=16-байт GUID, N=BCD-подобное, DT=7 байт, L=1 байт; PARTNO отсутствует в 8.1-эпохах); unit-тест на фикстуре
- [x] [fact] `source_8x_file`: чтение blob-цепочек (256-байтные чанки, размер в заголовке); unit-тест
- [x] [assumption] `source_8x_file`: парсер DBSCHEMA (SERIALIZEDDATA: блоки `{"ReferenceN","N",<id>,"",{FldNNN…}}`, типы R/N/S/L/E/V) → схема полей + привязка таблица↔объект по порядку; unit-тест на фикстуре
- [x] [assumption] `source_8x_file`: парсер конфигурации 8.1-эпохи (GUID-файлы zlib + root) → имена/синонимы объектов; unit-тест на фикстуре
- [x] [assumption] `read_metadata()` интегрирована: объекты конфигурации + таблицы + поля → единая модель `model.py` (`to_model()`); unit-тест
- [x] [fact] Интеграционный тест: `1C_8.1` — каталог таблиц (517), метаданные «Банки» (Reference3 = `_REFERENCE3`), чтение записей справочника «Банки» (1141 запись, банки Узбекистана), декодирование строк/ссылок
- [x] [assumption] Интеграционный тест: приёмник `1C_8.3` — структура (8033 таблицы, camelCase `_Reference74`), чтение только каталога/схемы (read-only)
- [x] [assumption] `mcp_server`: тул `status` — состояние коннекторов (файл/HTTP/SQL), кеша (занято, попадания), последнего шага пайплайна; unit-тест (адаптированная идея из 1C:Platform Tools MCP)
- [x] [assumption] README: раздел «Парсер 1CD» (возможности, ограничения, статус фаз)

## Guard report

| Step | Status | Detail |
|------|--------|--------|
| lint | SKIP | no lint script in package.json |
| type | PASS | ok |
| test | PASS | [orion] no failures detected — summary:
 Test Files  10 passed (10)
      Tests  10 passed (10)
   Duration  667ms (transform 606ms, setup 0ms, collect 997ms, tests 51ms, environment 3ms, prepare 1.92s)

[orion: −1439 B (−87.6%) ≈ 360 tok — ≈ tokens: bytes/4 estimate (no tokenizer)] |
| drift | PASS | matched 1 exported capabilities |
| yagni | PASS | no snippets to check (repo median: 75 LOC, 3 imports) |
| economy | PASS | cache 5.8 KB of 100.0 MB (18 entries) — within budget; ≈ 460546 tok saved across 331 compress op(s) |
| security | PASS | no obvious issues |
| policy | PASS | no .orion/policy.json — no project gates to enforce |
| verifiability | PASS | oracles: test-runner, type-check · verifiability level 3 — strong checks present |

## Artifacts

- `changes/1-8-x-1cv8/proposal.md`
- `changes/1-8-x-1cv8/design.md`
- `changes/1-8-x-1cv8/tasks.md`
- `changes/1-8-x-1cv8/result.md`
- `reports/1-8-x-1cv8/guard-report.md`
- `changes/1-8-x-1cv8/specs/parser-1cd/spec.md`
- `changes/1-8-x-1cv8/snippets/`

## Уроки и решения

> missing exported: parser-1cd → fix the drift check, then re-run orion shield 1-8-x-1cv8
> [mcp-python-1-7] task not green: [assumption] `source_8x_file`: СВОЙ парсер `1Cv8.1CD`: заголовок, страницы, таблицы, — Command failed: pnpm vitest run tests/assumption_source_8x_file_1cv8_1cd.test.ts · Error: Command failed: pnpm vitest run tests/assumptio → fix the task, then re-run orion forge mcp-python-1-7
> [mcp-python-1-7] task not green: [assumption] Интеграционный тест чтения на реальной базе `БАЗА 31.07.202` — Command failed: pnpm vitest run tests/assumption_31_07_202.test.ts · Error: Command failed: pnpm vitest run tests/assumption_31_07_202.test.ts → fix the task, then re-run orion forge mcp-python-1-7
> [mcp-python-1-7] task not green: [assumption] `extension_83`: исходники расширения 1С 8.3 (XML): HTTP-сервис `GET /metadata`, `POST /load` (создание/обновление объектов, табличные части); README по сборке/установке в 1С — Command failed: pnpm vitest run tes → fix the task, then re-run orion forge mcp-python-1-7
> [mcp-python-1-7] task not green: [spike] Файлы объектов 8.1-эпохи: полный layout (реквизиты, табличные части, типы, — Command failed: pnpm vitest run tests/spike_8_1_layout.test.ts · Error: Command failed: pnpm vitest run tests/spike_8_1_layout.test.ts → fix the task, then re-run orion forge mcp-python-1-7
> [mcp-python-1-7] task not green: [fact] `v77_metadata`: парсер `1Cv7.MD` (OLE2, olefile): список справочников, документов, — Command failed: pnpm vitest run tests/fact_v77_metadata_1cv7_md_ole2_olefile.test.ts · Error: Command failed: pnpm vitest run tests/ → fix the task, then re-run orion forge mcp-python-1-7

## Next steps

The change passed every guard-rail and all tasks are done — ready to archive.
