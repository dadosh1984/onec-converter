# Changelog

Все заметные изменения для пользователя. Формат — по убыванию версий.
Версия — SemVer, монотонно растёт; номер фазы — в описании релиза.

## 0.22.0 (2026-08)

### DX и продукт (Фаза 39)
- `load --dry-run`: демо-план (объекты/режим/приёмник) без записи/отправки.
- `shell --source-dir`: интерактивный REPL исследования базы (tables,
  describe, query ...., help, exit; автодополнение через readline).
- Makefile: lint/type/test/bdd/gates/bench/clean; pre-commit hook
  (.githooks) блокирует 1CD/dump/jsonl в коммиты.
- README: «Быстрый старт за 5 минут» вверху; бейдж PyPI.
- Ворота: pytest (+5), conformance, ruff, mypy (50), check_bsl, vitest.

## 0.21.0 (2026-08)

### Мониторинг и DevOps (Фаза 38)
- progress.py: WorkflowProgress (строки/объекты/ошибки/объёмы/строк-сек);
  `metrics` выводит Prometheus-метрики прогресса.
- s3_client.multipart_upload: create/upload_part/complete (SigV4) для
  больших отчётов, abort при сбое; <= chunk_size делегирует put_object.
- gates.sh: цель `docker` (build, опц.); ci.yml — docker run smoke.
- docker-compose.yml: пример onec-converter + MinIO для S3-экспорта.
- nightly-bench workflow + scripts/benchmark.py (fake-база, время/скорость).
- Ворота: pytest (+5), conformance, ruff, mypy (49), check_bsl, vitest.

## 0.20.0 (2026-08)

### Безопасность и комплаенс (Фаза 37)
- pii_scanner.py: ИНН/СНИЛС/карты (Луна)/телефоны (РФ и UZ)/ПИНФЛ/e-mail,
  scan_text/scan_record/field_is_pii, профиль UZ (152 УЗ).
- audit: tamper-evident JSONL — SHA-256 hash-цепочка (prev_hash/hash) +
  verify_audit; pii_masking (автоскрытие ПДн в obj/detail/guid).
- РБАС MCP (env ONEC_MCP_ROLE=inspect|load): тул load_direct требует роль
  load; иначе RbacError.
- gdpr_152_report.py + CLI pii-report --audit-file [--rules-file --profile]:
  отчёт для службы безопасности (поля, алгоритмы, где логи).
- Ворота: pytest (+10), conformance, ruff, mypy (48), check_bsl, vitest.

## 0.19.0 (2026-08)

### SQL-источники PostgreSQL / MS SQL (Фаза 36)
- sql_source.py: контракт SqlSource (list_tables/fetch_metadata/fetch_rows),
  GenericSqlSource адаптер поверх драйвера (ленивый импорт psycopg2/pyodbc),
  SqlSourceError с подсказкой; build_sql_source(kind, dsn[, driver]).
- `extract --source-kind 1cd|postgres|mssql`, `--source-url`: извлечение из
  ИБ на сервере вместо файла 1Cv8.1CD (таблицы _Reference*/_Document*/
  _InfoRg*/_AccumRg*/_Enum* через information_schema).
- Честная [spike]-граница: детальный парсинг v8_metadata ограничен —
  документировано в README.
- Тесты +5 на mock-драйвере (без реальных серверов).
- Ворота: pytest (+5), conformance, ruff, mypy (46), check_bsl, vitest.

## 0.18.0 (2026-08)

### Регистры и перечисления (Фаза 35)
- enum_mapper.py: авто-маппинг значений перечислений по нормализованным
  именам (normalize_enum_name / build_enum_map / map_enum_value) — регистры
  и поля перечислений переносятся даже при перестановке/переименовании.
- Регистры: подтверждено, что _InfoRg/_AccumRg пишутся той же механикой
  append_records; добавлены тесты на запись строк регистра.
- transform: тесты применения enum-маппинга (имя и словарь имя->имя).
- docs/recipes/перенос-остатков-регистры.md — руководство по переносу
  остатков/оборотов и перечислений.
- Ворота: pytest (+7), conformance, ruff, mypy (45), check_bsl, vitest.

## 0.17.0 (2026-08)

### Производительность ядра (Фаза 34)
- index_rebuilder + `load --direct --index-repair`: генерация скрипта
  восстановления индексов (1cv8 /TestAndRepair или chdbfl) для приёмника
  после прямой записи.
- `extract --workers N`: параллельное чтение независимых таблиц
  (порядок строк сохранён, вывод детерминирован — тест).
- Подтверждено: mmap-чтение 1Cv8.1CD уже реализовано (read_page — срез
  памяти); table_stats читает только данные и кешируется.
- Ворота: pytest (+5), conformance, ruff, mypy (44), check_bsl, vitest.

## 0.16.0 (2026-08)

### JWT-контур целиком (Фаза 33)
- CLI `mint-token --secret [--issuer --exp-min]`: выпуск локального HS256
  JWT Bearer-токена на общем секрете (без OAuth2-сервера).
- `load --http --secret`: локальный mint-token — клиент выпускает JWT на
  месте и шлёт Authorization: Bearer (token_url/secret взаимоисключающие).
- extension_83/README + README: документированы три режима аутентификации
  (X-API-Key, OAuth2, локальный mint-token).
- тесты +6: mint-token CLI, согласование mint_jwt с BSL-логикой
  ПроверитьJWT (base64url+HMAC-SHA256 по схеме Module.bsl), secret-режим
  HttpClient83 (Bearer без X-API-Key).

## 0.15.0 (2026-08)

### Дефекты по итогам внешнего анализа (Фаза 32)
- clone_db: инвалидация кеша приёмника — ключ считается по прежнему файлу
  ДО перезаписи (повторное клонирование больше не отдаёт старые метаданные).
- base_health: include_rows=False по умолчанию (health-пинг больше не читает
  данные всех таблиц), sample_tables=N — выборка по длине строки; MCP-тул
  получил опцию include_rows.
- check_bsl добавлен в scripts/gates.sh (локальный паритет с ci.yml).
- audit: один открытый handle + периодический flush; ротация JSONL по размеру.
- notify: retry с экспоненциальным backoff при сетевых сбоях (4xx не ретраятся).
- openapi: securitySchemes BearerAuth (JWT); /load принимает Bearer; спека
  сверяется с реальными путями тестом.
- CLI extract: потоковое сохранение save_json_stream (закрыт OOM на больших
  базах; по-прежнему валидный JSON-массив).
- extension_83/Module.bsl: constant-time сравнение X-API-Key (Совпадает).
- Ворота: pytest (+14), conformance, ruff, mypy (43), check_bsl, vitest.

## 0.14.0 (2026-08)

### Аудит команд и внедрение навыков (Фаза 29)
- `docs/commands-map.md`: карта команд — CLI (20) + MCP (13), входы/выходы,
  поток данных, next-цепочки; проверка взаимосвязей (реестр CLI 20/20,
  аргументы --source-dir/--out/--format согласованы).
- `export-kd3 --rules rules.json [--out kd3.xml]`: экспорт правил TOON
  в XML в стиле КД3 (DataContainer/Rules/Attributes/EnumMappings) для
  ревью/переноса (авторский упрощённый формат, не бинарный КД3 1С).
- `search_schema`: покрыто тестами расширение на документы/регистры и
  поиск по синонимам (реализовано ранее, подтверждено).
- План: Фаза 29 ✅ (29.1 инвентаризация + 29.2 навыки).
- Тесты: согласованность реестра, commands-map, export-kd3, search_schema
  (+6).
- Ворота: pytest (все), conformance, ruff, mypy, vitest — зелёные.

## 0.13.0 (2026-08)

### DX: BDD-сценарии, Sonar-отчёт, OpenAPI-спека (Фаза 28)
- BDD-обёртка сквозных сценариев: `tests/bdd.py` — given/when/then-DSL на
  pytest-фикстурах (без новых зависимостей) + сценарий миграции
  extract→transform→load→verify на синтетике.
- `onec-converter sonar-report`: отчёт ruff в формате SonarQube Generic Issue
  Import (XML/JSON) — CI-интеграция (--target, --format, --out).
- OpenAPI-спека приёмника `docs/openapi.yaml`: генерируется из кода
  (scripts/gen_openapi.py: пути из http_client.py, обработчики из Module.bsl).
- README → «Разработка и качество».
- Тесты: BDD-сценарий + хелперы, sonar (JSON/XML/ошибки), openapi (+9).
- План: Фаза 28 ✅.

## 0.12.0 (2026-08)

### Мониторинг и интеграции (Фаза 27)
- `health.py` + MCP-тул `base_health(source_dir)`: версия ИБ, таблицы/строки,
  lock-файлы (1Cv8.1CL/1Cv8tmp*), свободное место, размер — «здоровье базы»
  для агента (идея OneS2Zabbix).
- `s3_client.py`: экспорт отчётов в S3 — `dump-report --file X --s3 bucket`
  (JSON/XLSX) через авторский минимальный SigV4-клиент (stdlib, без boto3);
  кастомный `--endpoint` для MinIO/Yandex Object Storage; ключи --key/--secret
  или env AWS_*.
- `notify.py`: webhook-хук (HTTP POST JSON) и Telegram (`--notify-url`,
  `--notify-telegram token:chat_id`) по завершении `load` — best-effort,
  сбой доставки не меняет результат.
- README → «Мониторинг и интеграции».
- Тесты: health на синтетике (+lock-файлы), SigV4 сверен с эталоном
  botocore, S3-мок (PUT+Authorization), webhook-мок (всего +11).
- План: Фаза 27 ✅.

## 0.11.0 (2026-08)

### Новые коннекторы: техжурнал + релиз конфигурации (Фаза 26)
- `source_techlog.py`: техжурнал 1С как ИСТОЧНИК — события (время, уровень,
  процесс, направленность, контекст, событие, поля) из каталога логов
  (*.log/*.lgp); фильтры process/event/level_min/tail, out_file JSON.
- `fetch_config.py`: `fetch-config` — релиз конфигурации (XML-выгрузка,
  Configuration.xml) как источник метаданных {kind, name, uuid}; двоичные .cf
  не поддерживаются (честная ошибка с подсказкой).
- CLI: подкоманды `techlog` и `fetch-config`; INFO-события в журнале аудита.
- docs/format-8x.md → «Техжурнал 1С (спайк)»; README — источники.
- Тесты: парсинг/фильтры/ошибки техжурнала, XML-релиз (всего +11).
- План: Фаза 26 ✅.

## 0.10.0 (2026-08)

### Audit-логирование миграции (Фаза 25)
- Новый модуль `audit.py`: AuditLog (JSONL: время/уровень/операция/объект/
  GUID/правило/результат), set_audit/get_audit (env ONEC_AUDIT_FILE для MCP),
  read_audit; уровни INFO/WARN/ERROR.
- Интеграция: load_direct — событие на каждый перенесённый объект (GUID
  приёмника), WARN по ненайденным ссылкам, сводка; transform/extract (CLI) —
  по-объектно; MCP step_extract.
- CLI: --audit-file (extract/transform/load) + подкоманда `audit --file`
  (фильтры --level/--op/--obj, --tail, --json, сводка по уровням).
- docs/playbook.md → «Аудит переноса (ПДн)»; README — audit.
- Тесты: журнал/уровни/JSONL, load_direct, transform ok+error, extract,
  CLI-фильтры (+6).
- План: Фаза 25 ✅.

## 0.9.0 (2026-08)

### Полный сценарий копии базы (Фаза 24: clone-db + rollback)
- CLI `clone-db --source-dir --target-dir [--with-rules]`: полная побитовая
  копия 1Cv8.1CD в новый каталог (оригинал read-only), кеш-сброс по новому
  ключу (`Cache.drop`), опция «стенд» — правила маппинга рядом (target/rules/).
- Снапшот до миграции: `load_direct` автоматически сохраняет
  workdir/snapshot.1CD приёмника до записи (откат при сбое); опция
  `--no-snapshot` (CLI load, MCP load_direct no_snapshot).
- Новый модуль `clone_db.py` (CloneError); CLI-подкоманда clone-db.
- Тесты: clone-db на синтетике (побитовая копия, rules, ошибки), CLI,
  snapshot/restore при сбое, no-snapshot, Cache.drop (+6).
- docs/recipes: шаг «стенд через clone-db»; README — clone-db/snapshot.
- План: Фаза 24 ✅.

## 0.8.0 (2026-08)

### Conformance-тесты MCP + CI-гейты (Фаза 23)
- `tests/test_mcp_conformance.py` (5 проверок): initialize-рукопожатие,
  tools/list (реестр без дублей 29.1), tools/call, изолированная ошибка
  неизвестного тула (сервер жив), поле `next` в ответах. E2E через
  stdio-транспорт из коробки клиента mcp 1.x.
- `scripts/gates.sh conformance` — отдельная цель ворот + шаг в CI
  (.github/workflows/ci.yml).
- `scripts/gates.sh --coverage pytest` — pytest-cov на новых модулях
  (objects_filter, jwt_auth, cache, http_client, mcp_server), порог 70%
  (сейчас 87%).
- docs/playbook.md → «MCP conformance»; README — conformance/coverage.
- План: Фаза 23 ✅.

## 0.7.0 (2026-08)

### Сокращение MCP-туллов (Фаза 29.1)
- `query_table` → удалён (объединён с `query_sql`, WHERE-синтаксис совместим).
- `table_sizes`/`table_sizes_report` → `table_sizes(..., format="json|xlsx")`.
- `structure_report`/`compare_structures` →
  `compare_structures(..., format="json|xlsx")`.
- MCP-туллы: 15 → 12; CLI-поверхность не тронута; плейбук и доки обновлены.

## 0.6.0 (2026-08)

### Селективный перенос по разделам (Фаза 29.2)
- `extract --objects "Справочник.Номенклатура,Документ.*"` — фильтр по
  конфигурационным объектам (kind+имя из read_metadata), группы
  `Справочник.*`/`Документ.*`/`Регистр.*`, физические таблицы
  `Таблица._REFERENCE3`; без `--objects` — все данные (по умолчанию).
- MCP `step_extract` — параметр `objects` (селективный перенос).
- Новый модуль `objects_filter.py` (парсер+матчер спецификаций); ошибки
  формата — понятное сообщение CLI.
- Тесты: unit (парсер/матчер), CLI 8.x (физическая таблица), реальная база
  8.1 (маппинг групп), MCP (step_extract objects).

## 0.5.0 (2026-08)

### Безопасность приёмника — OAuth2 + JWT (Фаза 22)
- `HttpClient83`: OAuth2 client-credentials — получение Bearer-токена
  (`token_url`/`client_id`/`client_secret`), кеш до expires_in, авто-обновление
  при 401; fallback на `X-API-Key` при отсутствии `token_url`.
- `Module.bsl`: проверка Bearer-JWT (подпись HMAC-SHA256 ключом — тем же
  секретом, срок жизни `exp`, issuer `ОжидаемыйIssuer`) — чистая 1С, без
  внешних библиотек; дополняет shared-secret (принимается ключ ИЛИ токен).
- `jwt_auth.py`: подпись/проверка HS256 на stdlib (эталон для BSL).
- Конфиг: `onec.toml` секция `[auth]` (`token_url`/`client_id`/`client_secret`)
  + флаги `load --token-url/--client-id/--client-secret`.
- Тесты: mint/verify JWT (истёкший/неверная подпись/чужой issuer → отклонён),
  OAuth2-поток на mock-транспорте (Bearer, кеш, refresh при 401).
- Документация: README и extension_83/README — раздел «Аутентификация
  приёмника (OAuth2/JWT)».

## 0.4.0 (2026-08)

### Качество и DX (Фаза 31)
- Кеш: TTL/лимит размера с L RU-эвикцией (`Cache.trim`); `stats()` показывает
  возраст самых старых данных — каталог не растёт бесконтрольно.
- Анонимизатор: fuzz-тест (случайные строки и обычные фразы не портятся) —
  защита от регрессии «маскирование произвольных текстов».
- `Module.bsl`: перед поиском в режиме `replace` ключ/наименование
  нормализуются (`СокрЛП`) — не создаётся дублей из-за пробелов/регистра.
- Документация аутентификации приёмника (`ОжидаемыйКлюч`, `--api-key`, `onec.toml`).

## 0.3.0 (2026-08)

### Надёжность (Фаза 30)
- Единый источник версии (`onec_converter.__version__`) — версия не расходится
  между pyproject/cli/тестами.
- Статическая проверка .bsl (`scripts/check_bsl.py`) — ловит дубли функций и
  не-Экспорт обработчики HTTP до вставки в 1С.
- CI: авто-проверка сборки пакета (`build + twine check`) и docker-образа.
- Защита от регрессий вне периметра pytest (Module.bsl, Dockerfile, версия).

### Исправления
- Module.bsl: восстановлен обработчик `ЗаписьДанных(Запрос) Экспорт` (был
  ошибочно переименован — модуль не компилировался в 1С).
- Dockerfile: установка пакета после копирования `src` (раньше образ не
  собирался); файлы LICENSE/README включены.
- Анонимизатор: маскирование ФИО не портит произвольные фразы
  («красный диван», «Ноутбук Lenovo») — маскируются только полные ФИО
  из 3 слов с заглавной; безопасность данных важнее редкой недомаскировки.
- CLI `load`: добавлены `--api-key`/`--retries` для HTTP-приёмника.

## 0.1.0 (2026-08)

### Возможности
- Перенос данных между ИБ 1С (7.7, 8.1–8.3) без платформы: собственный парсер
  `1Cv8.1CD`, пайплайн «inspect → extract → map → transform → load → verify».
- Управление через MCP-сервер (Claude/Cursor) или CLI.
- Прямая запись в **копию** базы (`load_direct`): справочники, документы со
  ссылками и табличными частями, регистры (сведений/накопления); верификация
  после записи, атомарная замена.

### Безопасность
- Анонимизатор ПДн (ФИО любой формы и регистра, телефоны, ИНН); режим
  псевдонима через HMAC; профили 152-ФЗ (salary/retail/medical).
- HTTP-приёмник (`Module.bsl`): аутентификация по `X-API-Key`, транзакции
  на объект с частичным отчётом ошибок, поддержка `replace` (обновление) и
  документов.
- Строгая валидация (`strict`) перед записью: длины строк, диапазоны чисел,
  даты, GUID-ссылки.
- Ретраи HTTP при 5xx с экспоненциальной задержкой; понятные ошибки.

### Производительность и DX
- Потоковый extract (`--stream`) для больших баз без OOM.
- `dump-records`: быстрый вывод строк таблицы (JSON/CSV) для отладки правил.
- Конфиг-файл `onec.toml` для повторяющихся параметров.
- `doctor`, `cache stats|clear`, `--strict-steps` в `scripts/gates.sh`.
- CI (GitHub Actions), LICENSE (MIT), условный vitest в воротах.
- Тесты — в `E:\test` (не забивают системный tmp).

### Известные ограничения
- Индексы таблиц **не пересобираются** (Фаза 14) — 1С может не сразу увидеть
  новые строки по индексируемым полям.
- Пустые таблицы (`data_page=0`) пока не записываются; `1Cv8.dt` и серверные
  (SQL) ИБ не поддерживаются.
