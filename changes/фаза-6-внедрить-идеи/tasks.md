# Tasks — фаза-6-внедрить-идеи

## Трек A — парсер и данные (`source_8x_file.py`)

- [ ] [assumption] Генератор синтетической мини-1CD `build_fake_1cd(path, tables, rows)`: валидный заголовок 1CDBMSV8 + root-объект (FAT level 0/1, каталог таблиц) + blob-таблицы + строки; unit-тест: `Database1CD` читает сгенерированную базу (каталог, таблицы, поля, записи) — основа unit-тестов без реальных 2.5-ГБ баз (идея: dt-demo-configuration)
- [ ] [assumption] Кеш ссылок GUID→наименование: `read_table(..., resolve_refs=True)` подставляет имя объекта для REF-полей (RV/B) через lazy-кеш имён (blob_page+IDRREF → имя из описания или первого строкового поля); unit-тест на синтетической базе; интеграционный тест на 1C_8.1 («Банки» → имена банков Узбекистана) (идея: tool1cd/onec_dtools кеш ссылок)
- [ ] [fact] Размеры таблиц в `status`-туле: `table_sizes` — число строк и объём данных на таблицу (ленивое вычисление + кеш); unit-тест на синтетической базе; интеграционная проверка на 1C_8.1/1C_8.3 (идея: 1C_PrometheusExporter метрики)
- [ ] [assumption] Журнал метрик времени `Timings`: histogram read_metadata/read_table по типу объекта (ms), доступен в `status`; unit-тест (идея: 1C_PrometheusExporter / БСП «Оценка производительности»)
- [ ] [fact] CP1251→UTF-8 middleware: параметр коннектора `encoding` (cp1251 для 7.7-источника по умолчанию, utf-8 для 8.x); перекодирование текстовых полей на стыке чтения строк; unit-тест (идея: кодировки 7.7-источников)

## Трек B — конвертация (`mapping_rules.py`, `transform.py`)

- [ ] [assumption] TYPE_PRIORITY: детерминированный порядок типов Str < Num < Date < Bool < Ref при конвертации полей (адаптация `_DBNAME_PRIORITY` Фазы 5); `resolve_type_priority(types) -> type`; unit-тест (идея: 1cdtools TYPE_PRIORITY)
- [ ] [assumption] TOON — таблица соответствий объектов/полей: JSON-правила маппинга «источник→приёмник», валидация правил, применение в `transform.py`; unit-тест (идея: Конвертация данных 3, TOON)
- [ ] [assumption] Импорт правил обмена КД3: парсер XML правил конвертации/регистрации (формат «Конвертации данных 3») → JSON-правила TOON; unit-тест на XML-фикстуре (идея: otymko/gitrules)
- [ ] [assumption] Анонимизатор PII: маскировка ФИО/телефонов/ИНН по regexp-маскам или списку реквизитов при выгрузке; параметр пайплайна `anonymize`; unit-тест (идея: маскирование персональных данных)

## Трек C — MCP-интерфейс (`mcp_server.py`)

- [ ] [assumption] MCP-тул `search_schema(query)`: двунаправленный поиск метаданные↔таблицы/поля («Номенклатура» ↔ «REFERENCE106»), возврат совпадений с типами; unit-тест (идея: alexkmbk/1CDBStorageStructureInfo)
- [ ] [assumption] MCP-тул `compare_structures(source, target)`: объекты/поля только в источнике / только в приёмнике / различающиеся типы; XLSX-отчёт; unit-тест (идея: RDT1C анализ конфигураций)
- [ ] [assumption] MCP-тул `query_table(table, filters, limit)`: выборка записей `read_table` с фильтрами `field op value`; unit-тест (идея: RequestConsole9000/consquery консоль запросов)

## Трек D — инфраструктура

- [ ] [assumption] `dump_metadata(path, fmt=yaml|json)`: экспорт метаданных базы в git-дружественный текст для диффов; unit-тест (идея: 1C-Company/GitConverter)
- [ ] [assumption] `docs/ideas.md`: список всех идей Фазы 6 с обоснованием и источником; README обновлён
