# Forge Report — фаза-6-внедрить-идеи

- **Status:** paused
- **Done:** 0 · **Skipped (cache):** 0 · **Pending:** 14
- **Generated:** 2026-08-08T12:05:46.709Z

| Task | Status |
|------|--------|
| [assumption] Генератор синтетической мини-1CD `build_fake_1cd(path, tables, rows)`: валидный заголовок 1CDBMSV8 + root-объект (FAT level 0/1, каталог таблиц) + blob-таблицы + строки; unit-тест: `Database1CD` читает сгенерированную базу (каталог, таблицы, поля, записи) — основа unit-тестов без реальных 2.5-ГБ баз (идея: dt-demo-configuration) | pending |
| [assumption] Кеш ссылок GUID→наименование: `read_table(..., resolve_refs=True)` подставляет имя объекта для REF-полей (RV/B) через lazy-кеш имён (blob_page+IDRREF → имя из описания или первого строкового поля); unit-тест на синтетической базе; интеграционный тест на 1C_8.1 («Банки» → имена банков Узбекистана) (идея: tool1cd/onec_dtools кеш ссылок) | pending |
| [fact] Размеры таблиц в `status`-туле: `table_sizes` — число строк и объём данных на таблицу (ленивое вычисление + кеш); unit-тест на синтетической базе; интеграционная проверка на 1C_8.1/1C_8.3 (идея: 1C_PrometheusExporter метрики) | pending |
| [assumption] Журнал метрик времени `Timings`: histogram read_metadata/read_table по типу объекта (ms), доступен в `status`; unit-тест (идея: 1C_PrometheusExporter / БСП «Оценка производительности») | pending |
| [fact] CP1251→UTF-8 middleware: параметр коннектора `encoding` (cp1251 для 7.7-источника по умолчанию, utf-8 для 8.x); перекодирование текстовых полей на стыке чтения строк; unit-тест (идея: кодировки 7.7-источников) | pending |
| [assumption] TYPE_PRIORITY: детерминированный порядок типов Str < Num < Date < Bool < Ref при конвертации полей (адаптация `_DBNAME_PRIORITY` Фазы 5); `resolve_type_priority(types) -> type`; unit-тест (идея: 1cdtools TYPE_PRIORITY) | pending |
| [assumption] TOON — таблица соответствий объектов/полей: JSON-правила маппинга «источник→приёмник», валидация правил, применение в `transform.py`; unit-тест (идея: Конвертация данных 3, TOON) | pending |
| [assumption] Импорт правил обмена КД3: парсер XML правил конвертации/регистрации (формат «Конвертации данных 3») → JSON-правила TOON; unit-тест на XML-фикстуре (идея: otymko/gitrules) | pending |
| [assumption] Анонимизатор PII: маскировка ФИО/телефонов/ИНН по regexp-маскам или списку реквизитов при выгрузке; параметр пайплайна `anonymize`; unit-тест (идея: маскирование персональных данных) | pending |
| [assumption] MCP-тул `search_schema(query)`: двунаправленный поиск метаданные↔таблицы/поля («Номенклатура» ↔ «REFERENCE106»), возврат совпадений с типами; unit-тест (идея: alexkmbk/1CDBStorageStructureInfo) | pending |
| [assumption] MCP-тул `compare_structures(source, target)`: объекты/поля только в источнике / только в приёмнике / различающиеся типы; XLSX-отчёт; unit-тест (идея: RDT1C анализ конфигураций) | pending |
| [assumption] MCP-тул `query_table(table, filters, limit)`: выборка записей `read_table` с фильтрами `field op value`; unit-тест (идея: RequestConsole9000/consquery консоль запросов) | pending |
| [assumption] `dump_metadata(path, fmt=yaml|json)`: экспорт метаданных базы в git-дружественный текст для диффов; unit-тест (идея: 1C-Company/GitConverter) | pending |
| [assumption] `docs/ideas.md`: список всех идей Фазы 6 с обоснованием и источником; README обновлён | pending |

Waiting for implementation snippets:
- `changes/фаза-6-внедрить-идеи/snippets/assumption_1cd_build_fake_1cd_path_tables_rows_1cdbmsv8_root_fat.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_guid_read_table_resolve_refs_true_ref_rv_b_lazy_blob_.ts`
- `changes/фаза-6-внедрить-идеи/snippets/fact_status_table_sizes_unit_1c_8_1_1c_8_3_1c_prometheusexporter.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_timings_histogram_read_metadata_read_table_ms_status_.ts`
- `changes/фаза-6-внедрить-идеи/snippets/fact_cp1251_utf_8_middleware_encoding_cp1251_7_7_utf_8_8_x_unit_.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_type_priority_str_num_date_bool_ref_dbname_priority_5.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_toon_json_transform_py_unit_3_toon.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_3_xml_3_json_toon_unit_xml_otymko_gitrules.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_pii_regexp_anonymize_unit.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_mcp_search_schema_query_reference106_unit_alexkmbk_1c.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_mcp_compare_structures_source_target_xlsx_unit_rdt1c.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_mcp_query_table_table_filters_limit_read_table_field_.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_dump_metadata_path_fmt_yaml_json_git_unit_1c_company_.ts`
- `changes/фаза-6-внедрить-идеи/snippets/assumption_docs_ideas_md_6_readme.ts`
