# onec-converter — MCP-сервер переноса данных между ИБ 1С

Авторский проект (код пишется с нуля; чужие проекты — только источник идей о форматах).

## Возможности
- Перенос данных **из любой версии ИБ 1С** (7.7, 8.1, 8.2, 8.3) в **1С 8.x** (основной
  приёмник — 8.3) по командам LLM-агентов (Claude, Cursor) или из терминала (CLI).
- Работает **без платформы 1С** (Windows/Linux/macOS).
- Источники: 7.7 — каталог ИБ (`1Cv7.MD` + `1Cv77.dat`, текстовый формат, CP866);
  8.x — файловая ИБ `1Cv8.1CD` (собственный парсер).
- Пайплайн: init → inspect_source → extract → inspect_target → map → transform →
  prevalidate → preview → load → **verify** (сверка полноты 100%).
- Правило **«1→1»**: одна передающая ИБ = одна принимающая ИБ.
- **Кеш** метаданных/данных: повторный анализ базы 2–3 ГБ не перечитывает её целиком.
- Промежуточный формат: XML/JSON + человекочитаемый xlsx-отчёт.

## Установка
```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows
.venv/bin/pip install -e ".[dev]"        # Linux/macOS
```
После установки доступны две точки входа: MCP-сервер (`python -m onec_converter.mcp_server`)
и CLI (`onec-converter`).

## CLI (Фаза 9, без MCP)

Использование пайплайна из терминала, без MCP-клиента. Только stdlib (argparse),
все команды переиспользуют те же модули, что и MCP-сервер.

```
onec-converter --help
onec-converter <команда> --help
```

### inspect — метаданные источника
```
onec-converter inspect --source-dir "1C_8.1" --source-encoding cp866
# 7.7: sections, unique_ids, constants, references_tables
# 8.x: таблицы + размеры (rows/bytes)
```

### extract — данные источника → intermediate JSON
```
onec-converter extract --source-dir "1С_7.7" --out extract.json
onec-converter extract --source-dir "1С_7.7" --out extract.json \
    --encoding cp1251 --anonymize-fields "Фамилия,Телефон" --limit 1000 \
    --objects "Справочник.Номенклатура,Справочник.Контрагенты"
```

### map — правила маппинга (TOON)
```
onec-converter map --rules-file rules.json
onec-converter map --llm-prompt --meta-source ms.json --meta-target mt.json --out prompt.txt
```
`--llm-prompt` формирует промпт для LLM по метаданным обеих сторон **без вызова LLM**.

### transform — применение правил к intermediate
```
onec-converter transform --rules-file rules.json --input extract.json --out transformed.json
onec-converter transform --rules-file rules.json --input extract.json --preview 10   # dry-run
```

### load — загрузка батчей в приёмник (файл/HTTP)
```
onec-converter load --input transformed.json --target out/            # файл-приёмник
onec-converter load --input transformed.json --http http://host/base \
    --source-ib srcA --target-ib tgtX                                # HTTP-расширение 8.3
```
HTTP-режим использует `HttpClient83` с ретраями; при ошибках — exit 1 и отчёт.

### status — состояние пайплайна
```
onec-converter status --project-dir project/
```
Выводит JSON: коннекторы (file/http/sql), кеш (entries/bytes/hits), последний шаг, привязка 1→1.

## Подключение к Claude / Cursor
Пропишите MCP-сервер (stdio):
```
mcp: python -m onec_converter.mcp_server
```

## Порядок переноса (команды агенту)

Универсальная последовательность команд MCP-сервера — **плейбук**
(`docs/playbook.md`, тул `playbook()`): разведка (search_schema, table_sizes,
compare_structures) → инициализация пары → правила маппинга → извлечение →
загрузка → сверка. Ответ каждого тула содержит поле `next` — следующую
рекомендуемую команду, агент движется по плейбуку автоматически.

Каждое применение команды видно в терминале сервера (stderr):
`[onec-converter 17:38:13] ✔ table_sizes (82 ms) — ok=True, count=75`.
1. «Подготовь проект переноса: источник <путь>, приёмник <путь>» — init (правило 1→1).
2. «Изучи источник» — inspect_source (метаданные).
3. «Выгрузи справочник Номенклатура» — extract (+ xlsx-отчёт).
4. «Изучи приёмник» — inspect_target (через /metadata или 1Cv8.1CD приёмника).
5. «Составь правила переноса» — map (LLM по метаданным обеих сторон).
6. «Проверь перенос» — transform + prevalidate (количество, ссылки, дубликаты).
7. «Перенеси» — preview → load (пакетная запись через HTTP-сервис расширения).
8. «Проверь полноту» — verify (сверка источник ↔ приёмник).

## Приёмник 8.3 (временно — расширение)
Установите расширение `onec_loader` (см. `src/onec_converter/extension_83/README.md`):
HTTP-сервисы `GET /metadata` и `POST /load`. Целевая фича «zero-setup» —
прямая запись в `1Cv8.1CD` (research: `docs/zero-setup.md`).

## Ограничения (MVP)
- Справочники и документы без табличных частей (далее: табличные части, перечисления,
  регистры).
- Расширение приёмника собирается в 1С:Предприятие (до фичи zero-setup).
- 1Cv8.dt и серверные ИБ (SQL) — запасные/не реализованы.

## Парсер 1CD (собственный, `source_8x_file.py`)

Файловая ИБ 8.x (`1Cv8.1CD`) читается собственным парсером без платформы 1С:

- **Заголовок**: `1CDBMSV8` + версия, размер страницы (8192/4096), число страниц.
- **Root-объект** (страница 2): FAT level 0/1, цепочки blob-чанков по 256 байт —
  из них собирается каталог таблиц: локаль, число таблиц, описания
  (имя, поля, индексы, файлы данных/блобов/индексов).
- **Строки**: нарезка по row_length, декодирование полей:
  NVC (utf-16le с префиксом длины), NC, N (BCD-подобное), DT (7 байт), L, RV/B (GUID),
  NT, I; поле PARTNO в 8.1-эпохах отсутствует.
- **Blob-цепочки**: чанки 256 байт `[nxt:uint32][size:int16]` — данные BINARYDATA,
  DBSCHEMA (текст схемы, поля FldNNN), конфигурации (zlib raw).
- **Конфигурация 8.1-эпохи**: root + GUID-файлы (zlib inflate) — имена/синонимы объектов;
  привязка GUID ↔ таблица по DBNames (kind + номер): `_REFERENCE3`, `_DOCUMENT7` и т.п.
- **Два стиля имён таблиц**: 8.1-эпоха (`_REFERENCE3`) и 8.3 (`_Reference74`).
- Интеграция: `read_metadata()` (объекты + таблицы + поля) → `to_model()` —
  единая модель `model.py` (`ObjectType`/`AttrDef`); `read_table()` — потоковое чтение
  записей; `read_dbschema()` — текст схемы.
- Режим строго read-only; дескриптор живёт весь срок чтения.
- **Производительность**: чтение метаданных 8.3 (2545 объектов, 47 648 файлов
  конфигурации) — ~1.7s; 8.1 — ~0.1s. Кеш метаданных на диск (`.onec_cache/`,
  ключ по mtime/размеру/первым 64 КБ) — повторные вызовы за миллисекунды.
  Распаковка конфигурации ленивая (только запрошенные файлы), разбор
  скобкофайлов — частичный (`_object_name_fast`, без построения полного дерева).

Проверено на реальных базах: `1C_8.1` (517 таблиц, справочник «Банки» — 1141 запись,
банки Узбекистана) и `1C_8.3` (8033 таблицы, camelCase-стиль) — см. `test_source_8x_file.py`.
Формат задокументирован в `docs/format-8x.md`.

## Тесты
```
pytest                      # unit + интеграционные (реальные базы — read-only копии)
ruff check src tests
mypy src
```
Полный прогон (включая интеграционные на реальных базах 8.1 и 8.3):
~3.5s при холодном кеше метаданных, ~1s при тёплом (было 8–10 минут до
оптимизаций: ленивая распаковка конфигурации, индекс blob-смещений,
частичный разбор скобкофайлов).

## Фаза 6 — внедрённые идеи (см. `docs/ideas.md`)

Реализовано 12 идей внешних 1С-проектов (авторский код, только идея):

**Парсер и данные**
- `fake_1cd.py` — генератор синтетической мини-1CD для unit-тестов (dt-demo-configuration).
- `ref_name()`/`read_table(ref_tables=...)` — кеш ссылок GUID→наименование (tool1cd).
- MCP-тул `table_sizes` — размеры таблиц (1C_PrometheusExporter); `timings.py` — журнал метрик.
- `Base77(encoding=...)` — CP1251→UTF-8 middleware для 7.7 (кодировки 1Cv77.dat).

**Конвертация**
- `type_priority.py` — TYPE_PRIORITY Str<Num<Date<Bool<Ref (1cdtools); проверка в `validate_rules`.
- TOON-правила: `load_rules`/`save_rules` в `mapping.py` (Конвертация данных 3).
- `kd3_import.py` — импорт XML правил обмена КД3 → JSON (gitrules).
- `anonymizer.py` — маскировка PII: ФИО/телефоны/ИНН, режимы mask/hash.

**MCP-интерфейс и инфраструктура**
- `search_schema` — двунаправленный поиск метаданные↔таблицы (1CDBStorageStructureInfo).
- `compare_structures` — diff-отчёт структур двух баз (RDT1C).
- `query_table` — консоль запросов с фильтрами `Поле=знач; Поле>10` (RequestConsole9000).
- `dump_metadata` — экспорт метаданных в YAML/JSON для git-диффов (GitConverter).

## Сквозной перенос 7.7→8.3 (Фаза 7, `docs/pipeline.md`)

Полный сценарий одной командой — MCP-тул `migrate(project_dir, source_ib_id,
target_ib_id, source_dir, target_url, rules, out_file, source_encoding)`:
init → inspect_source → extract → map → transform → prevalidate → load
(HTTP /load приёмника 8.3). Каждый шаг логируется в терминал и возвращается
в `steps` ответа с временем; при ошибке — частичный прогресс и код ошибки.

```
[onec-converter 17:55:01] ─── шаг 1/7: init
[onec-converter 17:55:01] ▶ step_init(...)
…
```

Сквозные тесты (tests/test_pipeline_e2e.py): синтетика 7.7 (cp866 и cp1251)
→ TOON-правила → transform → validate → HTTP-mock приёмника 8.3;
контроль количества записей, кодировок (UTF-8), правила 1→1.

## Документация форматов
- `docs/format-77.md` — текстовый формат ИБ 7.7 (`1Cv77.dat`, `1Cv7.MD`).
- `docs/format-8x.md` — формат `1Cv8.1CD` (1CD 8.3.8.0), конфигурация, DBSCHEMA.
- `docs/zero-setup.md` — фича минимального вмешательства на приёмнике.
