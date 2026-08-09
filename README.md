# onec-converter — MCP-сервер переноса данных между ИБ 1С

![CI](https://img.shields.io/github/actions/workflow/status/dadosh1984/onec-converter/ci.yml?branch=main&label=CI)
![Python](https://img.shields.io/pypi/pyversions/onec-converter)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/github/v/tag/dadosh1984/onec-converter)
![PyPI](https://img.shields.io/pypi/v/onec-converter)

Авторский проект (код пишется с нуля; чужие проекты — только источник идей о форматах).

## Быстрый старт за 5 минут (Фаза 39)
1. **Установка**: `pip install onec-converter` (пакет на [PyPI](https://pypi.org/project/onec-converter/)).
2. **Извлечение** из источниковой ИБ 8.x:
   ```
   onec-converter extract --source-dir "./src" --out extract.json
   ```
3. **Правила и применение**: `map` (сгенерировать) → `transform --rules-file rules.json --input extract.json --out transformed.json`.
4. **Загрузка**: для стенда `clone-db` (копия приёмника), для боевой миграции — `load --direct ./tgt --input transformed.json --workdir ./work` (+ `--index-repair`).
5. **Проверка**: `verify`/`query`, аудит `--audit-file audit.jsonl`, метрики `metrics`.

Полный пайплайн и MCP-подключение к Claude/Cursor — ниже.

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

## Что переносим (и что — нет)

Инструмент переносит **пользовательские данные** — то, что пользователь 1С внёс
в ИБ вручную: справочники (номенклатура, контрагенты, банки…), документы
с табличными частями, регистры (остатки/обороты/сведения), значения
перечислений.

**Конфигурация (код, метаданные, формы, отчёты, права) НЕ переносится.**
Структура приёмника (метаданные) готовится отдельно — конфигурация приёмника
обновляется/настраивается штатными средствами (Конфигуратор, 1C:EDT, хранилище).
Наш инструмент переносит **данные** между структурами через правила маппинга
(TOON: поле источника → поле приёмника), включая перенос между РАЗНЫМИ
конфигурациями («Код» → «КодТовара» и т.п.).

## Чем отличается от альтернатив

- **onec_dtools / tool1cd / 1CDBStorageStructureInfo** — утилиты ЧТЕНИЯ
  формата `1Cv8.1CD`. onec-converter делает это сам, но, в отличие от них,
  покрывает весь пайплайн «сравнение структур → маппинг → перенос →
  верификация» под управлением LLM-агента (MCP) или CLI: промежуточный
  intermediate-формат / TOON-правила, прямой перенос в копию базы, отчёты.
- **Штатные «Конвертации данных 2.0/3.0»** — требуют платформу и знание
  XML-правил. здесь — Python CLI/Linux/macOS, маппинг через LLM-промпт.
- Отличие по возможностям — см. `docs/development-plan.md` и `docs/format-8x.md`.

## Установка
```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows
.venv/bin/pip install -e ".[dev]"        # Linux/macOS
```
После установки доступны две точки входа: MCP-сервер (`python -m onec_converter.mcp_server`)
и CLI (`onec-converter`).

Проверить окружение (версии mcp/PyYAML, доступность кеша) можно одной командой:
```
onec-converter doctor
```

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

**SQL-источники (Фаза 36):** извлечение из ИБ 1С на сервере, а не из файла
`1Cv8.1CD`:
```
onec-converter extract --source-kind postgres --source-url "dbname=ib host=/var/run/postgresql" --out extract.json
onec-converter extract --source-kind mssql --source-url "DRIVER=ODBC Driver 17;SERVER=srv;DATABASE=ib;UID=u;PWD=p" --out extract.json
```
Адаптер читает системные таблицы `information_schema`/`INFORMATION_SCHEMA`
(таблицы `_Reference*/_Document*/_InfoRg*/_AccumRg*/_Enum*`). Нужен драйвер:
`psycopg2` (PostgreSQL) или `pyodbc` (MS SQL), устанавливается отдельно;
structure конфигурации перенос регистрирует как [spike] — детальный парсинг
`v8_metadata` ограничен. Без `1Cv8.1CD` в `--source-dir` при `--source-kind`
не требуется.

**Селективный перенос по разделам (Фаза 29.2):** `--objects` фильтрует по
конфигурационным объектам (kind+имя из метаданных):
- точно: `Справочник.Номенклатура`, `Документ.БанковскиеВыписки`;
- группа: `Справочник.*`, `Документ.*`, `Регистр.*`;
- физическая таблица (8.x): `Таблица._REFERENCE3`;
- без `--objects` — переносятся **все** данные (по умолчанию).

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
    --source-ib srcA --target-ib tgtX --api-key секрет              # HTTP-расширение 8.3
```
HTTP-режим использует `HttpClient83` с ретраями; при ошибках — exit 1 и отчёт.

**Аутентификация приёмника (Фаза 22):** три режима.
1. **X-API-Key** (простой): `--api-key секрет` — заголовок `X-API-Key`.
2. **OAuth2 client-credentials** (JWT): `--token-url http://host/token \
   --client-id id --client-secret секрет` — клиент получает Bearer-токен
   (кеширует до expires_in, обновляет при 401) и шлёт его в
   `Authorization: Bearer <jwt>`. Приёмник проверяет подпись HS256
   (ключ — тот же секрет), срок жизни и issuer. Параметры можно задать
   в `onec.toml` секцией `[auth]`.
3. **Локальный mint-token** (Фаза 33, без OAuth2-сервера):
   `--secret секрет` — клиент выпускает HS256 JWT на месте
   (`onec-converter mint-token --secret секрет` для отдельных токенов)
   и шлёт `Authorization: Bearer <jwt>`. Секрет тот же, что задан
   в приёмнике (`ОжидаемыйКлюч` Module.bsl). `--token-url` и `--secret`
   взаимоисключающие.

```toml
[auth]
token_url = "http://host/token"
client_id = "migrator"
client_secret = "..."
```

### clone-db — полная копия базы (Фаза 24)
```
onec-converter clone-db --source-dir 1C_8.1 --target-dir stand/          # копия ИБ
onec-converter clone-db --source-dir 1C_8.1 --target-dir stand/ \
    --with-rules rules.json   # + правила маппинга рядом (сценарий «стенд»)
```
Полная побитовая копия `1Cv8.1CD` в новый каталог (оригинал read-only);
кеш метаданных по новому пути инвалидируется. При `--direct`-записи
`load` автоматически сохраняет `workdir/snapshot.1CD` приёмника до записи
(откат при сбое); отключить: `--no-snapshot`.

### export-kd3 — правила TOON в XML КД3-стиля (Фаза 29)
```
onec-converter export-kd3 --rules rules.json --out kd3.xml
```
XML-представление правил (DataContainer/Rules/Attributes/EnumMappings) для
ревью и переноса (авторский формат в стиле КД3). Карта всех команд —
`docs/commands-map.md`.

### shell — интерактивное исследование базы (Фаза 39)
```
onec-converter shell --source-dir ./src
> tables                      # список таблиц
> describe _Reference10       # поля/типы таблицы
> query _Reference10 WHERE Банк   # первые строки (лимит 20)
> exit
```

### AI-навыки для LLM-агентов (Фаза 40)
- MCP `auto_map_schemas(source_dir, target_dir)` — детерминированный
  авто-маппинг объектов/реквизитов по именам/синонимам → готовые правила TOON.
- MCP `explain_diff(source_dir, target_dir)` — человекочитаемые причины
  расхождений структур (а не сухие списки).
- `examples/context_compressor.md` — сжатие метаданных (тысяч объектов) до
  краткого саммари для контекста LLM (`compress_metadata`).
- `examples/autonomous_migration.md` — сквозной сценарий миграции по командам.

### Разработка и качество (Фаза 28)
```
onec-converter sonar-report --target src --format xml --out sonar.xml
onec-converter sonar-report --format json     # CI-артефакт
```
BDD-сценарии миграции — `tests/bdd.py` (given/when/then через pytest-фикстуры,
без новых зависимостей) + `tests/test_bdd_scenario.py` (сквозной сценарий
extract→transform→load→verify). Sonar: отчёт ruff в формате SonarQube
Generic Issue Import (XML/JSON). OpenAPI-спека приёмника — `docs/openapi.yaml`,
генерируется `scripts/gen_openapi.py` из кода (http_client + Module.bsl).

### Мониторинг и интеграции (Фаза 27)
```
onec-converter base_health --source-dir ./src          # MCP-тул: версия,
                                                       # строки, блокировки, место
onec-converter dump-report --file report.xlsx --s3 bucket     --endpoint https://minio.local --key AK --secret SK
onec-converter load --direct ./tgt --input batch.json --workdir ./work     --notify-url https://hooks.example/1c        # webhook по завершении
onec-converter load ... --notify-telegram token:chat_id   # Telegram-бот
```
`base_health` (MCP) — «здоровье базы»: версия ИБ, число таблиц/строк,
lock-файлы (1Cv8.1CL/1Cv8tmp*), свободное место. `dump-report` — экспорт
отчётов в S3 через авторский SigV4-клиент (endpoint — для MinIO/Yandex);
для больших файлов используется multipart-upload (Фаза 38).
Уведомления — best-effort: сбой доставки не ломает загрузку.

**Прогресс переноса (Фаза 38).** `onec-converter metrics` выводит Prometheus-
метрики прогресса: обработано строк/объектов, ошибки, объёмы, скорость
(строк/сек) — для Grafana/дашборда.

**Docker / Compose (Фаза 38).** Цель `docker` в `scripts/gates.sh` собирает
образ локально; CI делает `docker run --rm onec-converter:ci --version`
(smoke). `docker-compose.yml` — готовый пример связки onec-converter + MinIO
для S3-экспорта: `docker compose up -d`.

### techlog — техжурнал 1С как источник (Фаза 26)
```
onec-converter techlog --source-dir ./logs --process rphost --event EXCP     --level-min 3 --tail 50 --out events.json
```
События (SDBL/EXCP/TTIMEOUT, процесс, направленность, поля) — диагностика
активности и ошибок платформы до/после переноса.

### fetch-config — релиз конфигурации как источник (Фаза 26)
```
onec-converter fetch-config --source ./release --out meta.json
```
Метаданные конфигурации {kind, name, uuid} из XML-выгрузки 1С
(Configuration.xml) — структура приёмника без платформы. Двоичные .cf
не поддерживаются (честная ошибка с подсказкой).

### audit — журнал переноса (Фаза 25)
```
onec-converter load --direct ./tgt --input batch.json --workdir ./work     --audit-file audit.jsonl        # extract/transform/load пишут события
onec-converter audit --file audit.jsonl --level ERROR --op load   # фильтр
```
JSONL-журнал: время, уровень, операция, объект, GUID приёмника, правило,
результат (ПДн-аудит «кто/что/когда»). Для MCP — `ONEC_AUDIT_FILE` при
старте сервера. Журнал tamper-evident: каждая запись содержит `prev_hash`/
`hash` (SHA-256 цепочка) — проверка `verify_audit`; при `--pii-masking`
фрагменты ИНН/СНИЛС/тел в журнале скрываются.

### pii-report — отчёт по анонимизации ПДн (Фаза 37)
```
onec-converter pii-report --audit-file audit.jsonl --rules-file rules.json
# {profile, generated, pii_fields, algorithms, tamper_evident, audit_file}
```
Сводка для службы безопасности (152-ФЗ / 152 УЗ): какие поля были
анонимизированы, каким алгоритмом и где хранятся логи.

### RBAC в MCP (Фаза 37)
Роль клиента задаётся env `ONEC_MCP_ROLE` (`inspect` — только чтение,
`load` — полный доступ). Тул `load_direct` (прямая запись в 1CD) требует
роль `load`; read-only тулы (inspect/search_schema/query_sql/...) доступны
любой роли.

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
# Все ворота одним скриптом (pytest + MCP conformance + ruff + mypy + vitest):
bash scripts/gates.sh

# Опционально: вручную
pytest                      # unit + интеграционные (реальные базы — read-only копии)
bash scripts/gates.sh conformance   # E2E conformance MCP-сервера (Фаза 23)
bash scripts/gates.sh --coverage pytest  # + порог покрытия 70% на новых модулях
ruff check src tests
mypy src
npx vitest run              # .ts-сниппеты для Orion shield
```
Полный прогон (включая интеграционные на реальных базах 8.1 и 8.3):
~3.5s при холодном кеше метаданных, ~1s при тёплом (было 8–10 минут до
оптимизаций: ленивая распаковка конфигурации, индекс blob-смещений,
частичный разбор скобкофайлов).

Временные файлы тестов (копии реальных баз, сотни МБ) по умолчанию идут в
системный tmp; для больших баз задайте базовый tmp на диск с местом:
`ONEC_TEST_TMP=E:/test/.pytest-tmp bash scripts/gates.sh` (см. `pytest.ini`).

Статус: фазы 1–16 закрыты и заархивированы (`changes/archive/`); проект
≈98–100% (`docs/backlog.md`, `docs/ideas.md`, `docs/roadmap.md`).

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
- `compare_structures` — diff-отчёт структур двух баз (RDT1C), `format=json|xlsx`;
  `table_sizes` — размеры таблиц, `format=json|xlsx` (объединены с XLSX-отчётами Фазы 29.1).
- `query_sql` — консоль запросов: SQL-подобная выборка с WHERE-фильтрами
  `Поле=знач; Поле>10` (RequestConsole9000); `query_table` объединён сюда (Фаза 29.1).
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

## Прямая запись в 1CD (Фаза 10)

Загрузка в приёмник 8.x без HTTP-расширения — напрямую в файл базы.
**Только на копиях** (`write_8x.copy_1cd`); оригиналы не изменяются.

```python
from onec_converter.write_8x import copy_1cd, append_records

cp = copy_1cd('1C_8.3/1Cv8.1CD', 'copy.1CD')          # копия — рабочая
rows = b'\x00' * row_length * 100                     # тестовые строки
append_records(cp, '_REFERENCE3', rows)               # добавить в конец
```

- `create_1cd(path, tables)` — новая пустая база по структуре приёмника.
- `append_records(path, table, rows)` — добавление строк в конец таблицы:
  новые страницы данных, обновление FAT level 0/1 и длины объекта,
  total_pages. fat_level 1 (объекты > 8 МБ) поддержан (Фаза 12).
- Защита: `LockError`, если база открыта (`1Cv8.1CL`) или используется
  (`1Cv8tmp*`); `UserWarning` при записи в таблицу с индексами.
- Ограничения: пустые таблицы (data_page=0) не поддерживаются; индексы и
  BINARYDATA не пересобираются; индексы НЕ пересобираются — осознанное решение (Фаза 14, image-формат не расшифрован, запись вслепую небезопасна). Риск — `docs/format-8x.md`, «Индексы и запись»).
  Индексы не пересобираются — осознанное решение (Фаза 14): image-формат
  объекта индекса не расшифрован, запись вслепую небезопасна (`docs/format-8x.md`,
  «Индексы (Фаза 14, spike)»). Для 1С:Конфигуратор целостность восстанавливается
  через `load --direct --index-repair` (Фаза 34) — генерирует скрипт
  `/TestAndRepair` (1cv8) или chdbfl для ИБ-приёмника.

## Фаза 11 — новая порция идей (см. `docs/ideas.md`, трек E)

Пересмотр блок-листа идей после фаз 7–10; реализованы три:

| Идея | Модуль | CLI | MCP-тул |
|---|---|---|---|
| **E1** Консоль запросов конфигурации (SQL-подобный язык) | `query.py` — `query_table_sql` (SELECT/WHERE/ORDER BY/LIMIT, LIKE; REF → {guid,name}) | `onec-converter query` | `query_sql` |
| **E2** Сравнение ИБ по GUID (полнота переноса) | `guid_diff.py` — объекты и таблицы по стабильным GUID | `onec-converter guid-diff` | `guid_diff` |
| **E3** Версии конфигурации (формат/ИБ/платформа + дифф CONFIG↔CONFIGSAVE) | `config_versions.py` | `onec-converter config-versions` | `config_versions` |

Примеры:

```
onec-converter query --source-dir 1C_8.3 --table PARAMS \
    --select FILENAME,DATASIZE --where "FILENAME LIKE '%inf%'" --limit 10
onec-converter guid-diff --source-dir 1C_8.1 --target-dir 1C_8.3
onec-converter config-versions --source-dir 1C_8.3
```

Ограничения: история версий хранилища конфигуратора в файле базы отсутствует —
E3 даёт версии из файла и дифф последнего сохранения (`docs/format-8x.md`,
раздел «Версии и сохранения»).

## Прямая загрузка в 1CD (Фаза 13, zero-setup A)

Приёмник без HTTP-расширения: объекты (после transform) пишутся напрямую
в **копию** `1Cv8.1CD` через `load_8x.load_direct` (write_8x, Фазы 10–12).
Оригинал никогда не изменяется (`copy_1cd` + `LockError` при открытой ИБ).

```bash
onec-converter load --direct 1C_8.1 --input batch.json --workdir ./out
```

```python
from onec_converter.load_8x import load_direct
rep = load_direct('1C_8.1', objects, workdir='./out')   # {'ok', 'copy_path', ...}
```

Ограничения MVP: `_IDRREF` новых строк — префикс из существующих строк
таблицы + счётчик; индексы не пересобираются; простые реквизиты
(NVC/NC/N/L/DT).

Поскольку Фаза 15 `load_direct` поддерживает **документы со ссылками
и табличными частями**: REF-поля (`_FLD...RREF`) резолвятся в `_IDRREF`
приёмника по естественному ключу; документ-реквизиты `_NUMBER`/`_DATE_TIME`/
`_POSTED` берутся из атрибутов; табличная часть пишется в `_<Base>_VT<num>`
с parent-связью (`_<Base>IDRREF`) и `_LINENO`. Ненайденные ссылки → 16 нулей
+ `ref_warnings` (пакет не обрывается). Формат — `docs/format-8x.md`,
раздел «Ссылки и табличные части». Индексы (`_VT` в т.ч.) НЕ пересобираются
(Фаза 14).

Фаза 16 (надёжность): `load_direct(..., verify_after=True)` после записи
читает копию парсером и сверяет roundtrip без потерь (`verify.ok`); запись
атомарна (временный `work.1CD` → атомарный replace) — сбой не оставляет
полу-записи; лимиты (`max_objects`), нехватка диска (ENOSPC) → `LoadError`
с понятным текстом; tmp-файлы чистятся. Как проверить копию —
`docs/zero-setup.md` и `docs/playbook.md`. Подробнее — `docs/zero-setup.md`
и `docs/pipeline.md`.
