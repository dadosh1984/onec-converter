# Идеи Фазы 6 — источники и обоснование

Принцип проекта: берём **только идею** из внешнего проекта, усовершенствуем её
и реализуем **авторским кодом** (сторонние библиотеки 1С не включаются).
Источники: порядка 200 проектов 1С (изучены README/описания на GitHub) +
ранее изученные парсеры tool1cd/onec_dtools (зафиксировано в `format-8x.md`).

## Трек A — парсер и данные

| # | Идея | Источник | Реализация | Статус |
|---|------|----------|------------|--------|
| A1 | **Кеш ссылок GUID→наименование** | tool1cd/onec_dtools («кеш ссылок») | `read_table(..., ref_tables=...)`: REF-поля отдаются `{guid, name}` через lazy-кеш имён | ✅ `ref_name()`/`_build_ref_index()` |
| A2 | **Размеры таблиц в status** | 1C_PrometheusExporter (72★), ClusterMonitoring — метрики | MCP-тул `table_sizes` (строки/байты на таблицу, лениво+кеш) | ✅ `table_stats()` + тул |
| A3 | **Журнал метрик времени** | 1C_PrometheusExporter / БСП «Оценка производительности» (histogram, APDEX) | Лёгкий `Timings` + глобальный журнал; histogram read_metadata/read_table | ✅ `timings.py`, в `pipeline_status` |
| A4 | **CP1251→UTF-8 middleware** | Кодировки 7.7-источников (1Cv77.dat, CP866/CP1251) | Параметр `encoding` у `Base77`/`V77Reader`/`step_init`; перекодирование текстовых полей | ✅ `Base77(encoding='cp1251')` |
| A5 | **Генератор синтетической мини-1CD** | 1C-Company/dt-demo-configuration (демо-базы для тестов) | `build_fake_1cd(path, tables, rows)` — валидная маленькая файловая база | ✅ `fake_1cd.py` |

## Трек B — конвертация

| # | Идея | Источник | Реализация | Статус |
|---|------|----------|------------|--------|
| B1 | **TYPE_PRIORITY** | 1cdtools «TYPE_PRIORITY» | Детерминированный порядок типов Str < Num < Date < Bool < Ref; `resolve_type_priority(types)` | ✅ `type_priority.py` + проверка в `validate_rules` |
| B2 | **TOON — таблица соответствий** | Конвертация данных 3 (TOON — таблица соответствия объектов и реквизитов) | JSON-правила маппинга «источник→приёмник», валидация, применение в `transform.py` | ✅ `load_rules`/`save_rules` в `mapping.py` |
| B3 | **Импорт правил обмена КД3** | otymko/gitrules (71★) — разбор XML правил конвертации | Парсер XML правил «Конвертации данных 3» → JSON-TOON | ✅ `kd3_import.py` |
| B4 | **Анонимизатор PII** | Маскирование персональных данных (общая практика) | `anonymizer.py`: маскировка ФИО/телефонов/ИНН по regexp/списку реквизитов | ✅ `Anonymizer(fields, mode)` |

## Трек C — MCP-интерфейс

| # | Идея | Источник | Реализация | Статус |
|---|------|----------|------------|--------|
| C1 | **Двунаправленный поиск метаданные↔таблицы** | alexkmbk/1CDBStorageStructureInfo (34★) | MCP-тул `search_schema(query)`: поиск по «Номенклатура» и «REFERENCE106» | ✅ тул `search_schema` |
| C2 | **Diff-отчёт структур** | RDT1C (197★) «Инструменты разработчика» — анализ конфигураций | MCP-тул `compare_structures(source, target)`: объекты только в источнике/приёмнике, расхождения типов | ✅ тул `compare_structures` |
| C3 | **Консоль запросов** | RequestConsole9000 / consquery (консоль запросов) | MCP-тул `query_table(table, filters, limit)` — выборка с фильтрами | ✅ тул `query_table` |

## Трек D — инфраструктура

| # | Идея | Источник | Реализация | Статус |
|---|------|----------|------------|--------|
| D1 | **Экспорт метаданных в git-текст** | 1C-Company/GitConverter (276★) — конфигурация↔git | `dump_metadata(path, fmt=yaml|json)` | ✅ тул `dump_metadata` |
| D2 | **docs/ideas.md** | — | Каталог идей с обоснованием и статусом | ✅ этот файл |

## Не взято (и почему)

- **vanessa-automation / xUnitFor1C / yaxunit** — тесты на BSL внутри 1С; наш проект — Python, тесты уже на pytest.
- **deployka / vanessa-runner / 1C-Deploy-and-CopyDB** — управление платформой 1С через RAC/RAS; наш MCP работает напрямую с файлами (read-only), платформа не нужна.
- **1C_Sentry / Sentry_1C** — отправка ошибок в Sentry из 1С; ошибки нашего пайплайна уже логируются через MCP-ответы.
- **bsl-parser / bsparser / 1c-syntax** — парсеры кода BSL; мы не анализируем код, только данные и структуру.
- **OpenIntegrations (660★)** — интеграции с внешними API из 1С; у нас обратное направление — MCP наружу.
- **GitConverter целиком** — синхронизация хранилища конфигурации; взята только идея выгрузки метаданных в текст (D1).
- **liteExchange / FoxyLink** — фреймворки обмена внутри 1С; промежуточный формат у нас уже есть (`intermediate.py`).


## Трек E — Фаза 11 (пересмотр блок-листа)

| # | Идея | Источник | Реализация | Статус |
|---|------|----------|------------|--------|
| E1 | **Консоль запросов конфигурации** | RequestConsole9000 / consquery (пересмотр C3) | `query.py`: `query_table_sql` — безопасный SQL-подобный язык (SELECT/WHERE/ORDER BY/LIMIT, LIKE; REF → {guid,name}); CLI `query`, MCP `query_sql` | ✅ `query.py` + тул |
| E2 | **Сравнение ИБ по GUID** | 1CDBStorageStructureInfo (пересмотр C1) | `guid_diff.py`: объекты и таблицы двух баз по стабильным GUID (read_metadata + read_dbnames); CLI `guid-diff`, MCP `guid_diff` | ✅ `guid_diff.py` + тул |
| E3 | **Версии конфигурации** | 1C-Company/GitConverter (пересмотр D1) | `config_versions.py`: формат/ИБ/платформа + дифф CONFIG↔CONFIGSAVE («что изменилось с последнего сохранения»); CLI `config-versions`, MCP `config_versions` | ✅ `config_versions.py` + тул |

### Пересмотр «Не взято (и почему)» (Фаза 11)

- **История версий конфигурации** (как в хранилище конфигуратора) — в файле
  базы отсутствует; реализован честный суррогат: версии формата/ИБ/платформы
  + дифф CONFIG↔CONFIGSAVE (E3).
- Остальные пункты блок-листа (vanessa-automation, OpenIntegrations, deployka/RAC,
  bsl-parser, 1C_Sentry, GitConverter, liteExchange/FoxyLink) — причины не брать
  актуальны (см. выше), новых обстоятельств после фаз 7–10 нет.

## Итог


12 идей + документация — все реализованы в Фазе 6 (✅), 99 тестов зелёные.
Порядок: A (генератор → кеш → метрики → middleware) → B (приоритет → TOON →
импорт КД3 → анонимизатор) → C (поиск → diff → запросы) → D (git-текст →
ideas.md).
## После фаз 14–16 (блок-лист)

Результаты, добавляющие к блок-листу:

- **Запись в `1CD` (прямая)** — реализована (фазы 10–13, 15–16):
  `write_8x.append_records`, `load_8x.load_direct` в КОПИЮ, документы со
  ссылками и табличными частями, верификация и атомарность.
- **Индексы (B-tree)** — reverse-engineering (Фаза 14, spike): старый
  image-формат объекта индекса отличен от Tool1CD; битовая упаковка ключей
  не расшифрована, валидация реальной 1С невозможна. **Осознанный отказ** —
  оставлено «индексы не пересобираются» + `UserWarning`.

Остальные пункты блок-листа (vanessa-automation, OpenIntegrations, deployka/RAC,
bsl-parser, 1C_Sentry, GitConverter, liteExchange/FoxyLink) — причины не брать
актуальны; новых обстоятельств нет.
