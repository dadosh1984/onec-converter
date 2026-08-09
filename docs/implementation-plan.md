# План реализации идей (из аудита экосистемы) — фазы 22+

Источник идей: `docs/ideas-audit-2026.md` (200 репо + 6 MCP-конкурентов).
Философия: берём ТОЛЬКО идею, модернизируем (улучшаем) и внедряем
**авторским кодом**. Приоритет: безопасность → зрелость/CI → данные →
производительность → продукт/DX.

---

## Фаза 22 — Безопасность приёмника (OAuth2 + JWT) — ✅ выполнена

Идеи: vladimir-kharin/1c_mcp (OAuth2-прокси), pintov/1c-jwt (HMAC/JWT).

- [x] [fact] `http_client`: поддержка OAuth2-токена (client-credentials) —
      получение токена + автоматический заголовок; fallback на X-API-Key
- [x] [fact] `Module.bsl`: проверка Bearer-токена (JWT: подпись HMAC, срок жизни,
      issuer) — заменяет/дополняет shared-secret
- [x] [fact] конфиг: `onec.toml` — `[auth] token_url/client_id/secret` для приёмника
- [x] [fact] тесты: получение токена (mock), истёкший/неверный → 401, валидный → 200
- [x] [assumption] README/docs: раздел «Аутентификация приёмника (OAuth2/JWT)»

## Фаза 23 — Conformance-тесты MCP + CI-гейты

Идеи: DitriXNew/EDT-MCP (E2E/conformance на CI), yukon39/coverage-cli (покрытие).

- [ ] [spike] Что проверяет MCP conformance: список методов (initialize, tools/call, ✅
      resources), транспорт stdio/SSE, формат ошибок → docs/playbook.md
- [ ] [fact] conformance-набор: автотесты нашего mcp_server на соответствие ✅
      (initialize-рукопожатие, tools/list, tools/call, ошибки)
- [ ] [fact] CI: `.github/workflows/ci.yml` — добавить шаг conformance (vitest/pytest) ✅
- [ ] [fact] порог покрытия: `scripts/gates.sh` — опциональный `--coverage` (pytest-cov, ✅
      порог 70% на новые модули)
- [ ] [assumption] README/docs: бейдж coverage + описание conformance ✅

## Фаза 24 — Полный сценарий копии базы (clone-db + rollback)

Идеи: arkuznetsov/cpdb (копирование базы+MSSQL), Tavalik/Perezalivator (перезаливка).

- [ ] [fact] `onec-converter clone-db --source-dir --target-dir`: полная копия ✅
      структуры+данных файловой ИБ в новый каталог (файл-копия + кеш-сброс)
- [ ] [fact] `clone-db --with-rules`: вместе с правилами маппинга (сценарий «стенд») ✅
- [ ] [fact] снапшот до миграции: `load_direct` — автоматический `workdir/snapshot.1CD` ✅
      до записи; опция `--no-snapshot`
- [ ] [fact] тесты: clone-db на синтетике; snapshot/restore при сбое ✅
- [ ] [assumption] docs/recipes: обновить рецепт — шаг «создать стенд через clone-db» ✅

## Фаза 25 — Audit-логирование миграции

Идеи: oscript-library/logos (log4j-стиль), cpr1c/logosFor1c (сквозное логирование).

- [ ] [fact] `src/onec_converter/audit.py`: лог-записи (уровни INFO/WARN/ERROR; ✅
      время, операция, объект, GUID, правило, результат)
- [ ] [fact] интеграция: `load_direct`/`transform`/`extract` пишут audit-события ✅
      (каждый перенесённый объект: источник→приёмник, правило, время)
- [ ] [fact] CLI `onec-converter audit --file audit.jsonl` — просмотр/фильтр ✅
- [ ] [fact] тесты: audit-файл формируется, содержит GUID/правило/время ✅
- [ ] [assumption] docs: раздел «Аудит переноса (ПДн-соответствие)» ✅

## Фаза 26 — Новые коннекторы: техжурнал 1С + релизы конфигураций

Идеи: Polyplastic/1c-parsing-tech-log (327★), arkuznetsov/yard (релизы).

- [ ] [spike] Формат техжурнала 1С (каталог логов, события, поля) → docs/format-8x.md ✅
- [ ] [fact] `source_techlog.py`: чтение техжурнала как ИСТОЧНИКА (события/метаданные ✅
      операций) — мостик к диагностике миграции
- [ ] [fact] `fetch-config` (идея yard): загрузка релиза конфигурации (из каталога ✅
      поставки/`.cf`) как источника метаданных
- [ ] [fact] тесты: парсинг техжурнала на синтетике; fetch-config на фикстуре ✅
- [ ] [assumption] README/docs: источники «техжурнал», «релиз конфигурации» ✅

## Фаза 27 — Мониторинг и интеграции (health + S3 + уведомления)

Идеи: OneS2Zabbix/ClusterMonitoring (здоровье баз), 1c-s3connector (S3),
Bayselonarrend/OpenIntegrations (MCP-тулы наружу).

- [ ] [fact] MCP-тул `base_health(source_dir)`: число строк/ошибок/блокировки, ✅
      свободное место, версия ИБ — «здоровье базы» для агента
- [ ] [fact] экспорт результатов в S3: `dump-report --s3 <bucket>` (xlsx/json) ✅
      через boto3-подобный клиент (авторский, минимальный)
- [ ] [fact] уведомление по завершении: Telegram-хук (простой HTTP POST) в `load` ✅
- [ ] [fact] тесты: health на синтетике; S3-мок (запись в tmp); webhook-mock ✅
- [ ] [assumption] README/docs: раздел «Мониторинг и интеграции» ✅

## Фаза 28 — DX: BDD-сценарии, Sonar-отчёт, OpenAPI-спека

Идеи: artbear/1bdd (BDD), acc-export/stebi (Sonar), swagger-1c (OpenAPI).

- [ ] [fact] BDD-обёртка сквозных тестов: `given/when/then`-описание сценариев ✅
      миграции (через pytest-фикстуры, без новых зависимостей)
- [ ] [fact] `onec-converter sonar-report`: генерация отчёта lint/ruff в sonar-совместимом ✅
      формате (для CI-интеграции)
- [ ] [fact] `Module.bsl` + `swagger`: статическая OpenAPI-спека приёмника ✅
      (`docs/openapi.yaml`), сгенерированная из кода (скрипт)
- [ ] [fact] тесты: BDD-сценарий проходит; sonar-report валиден (XML/JSON) ✅
- [ ] [assumption] README/docs: раздел «Разработка и качество» ✅

---

## Приоритеты и зависимости

1. **Фаза 22** (безопасность) — критично, база для доверия.
2. **Фаза 23** (conformance/CI) — зрелость, ловит регрессии.
3. **Фаза 24** (clone-db/snapshot) — удобство стендов, без зависимостей.
4. **Фаза 25** (audit) — ПДн-соответствие, требует минимальной интеграции.
5. **Фаза 26** (техжурнал/релизы) — новые источники, spike в начале.
6. **Фаза 27** (мониторинг/S3/Telegram) — product-DX.
7. **Фаза 28** (BDD/Sonar/OpenAPI) — DX, финализация.

Каждая фаза: think → draft → ручная доводка design/tasks → локальная
реализация (вариант б) → forge → shield → out → коммит/пуш → **релиз** →
архивация.

**Релиз в конце каждой фазы** (см. RELEASING.md):
- бамп версии только `__init__.__version__` — SemVer монотонно (0.3.0, 0.4.0, …),
  НЕ номер фазы (см. RELEASING.md, Вариант A);
- публикация в TestPyPI → PyPI → GitHub Release (`bash scripts/release.sh`,
  или `git tag v<x.y.z> && git push --tags` + `.github/workflows/publish.yml`);
- обновить `CHANGELOG.md` (что появилось для пользователя).

Ворота: mypy strict, ruff, pytest, vitest; тесты в `E:	est`.

---

## Фаза 29 — Аудит команд и внедрение навыков (идей)

Сквозная работа: изучить каждую команду CLI/MCP, модернизировать её, внедрить
подходящие идеи из аудита и проверить взаимосвязи между командами.

### 29.1. Инвентаризация и взаимосвязи команд
- [ ] [spike] Карта команд: CLI (13) + MCP-туллы (15) — входы/выходы, поток данных ✅
      между ними (inspect→extract→map→transform→load→verify), общие аргументы,
      next-подсказки MCP → docs/commands-map.md
- [ ] [fact] Проверка взаимосвязей: каждая команда реально вызывается в пайплайне; ✅
      нет «мёртвых» команд/тулов, аргументы согласованы (одни и те же флаги
      --source-dir/--out и т.д.), next-цепочки корректны (см. playbook)
- [ ] [fact] Устранение рассинхронов (если найдены): документировать/чинить ✅
- [ ] [fact] Сокращение MCP-туллов (устранить дубли через --format): ✅
      объединить `query_table`→`query_sql` (удалить старый), 
      `table_sizes`/`table_sizes_report`→`table_sizes --format json|xlsx`,
      `structure_report`/`compare_structures`→`compare_structures --format json|xlsx`
      (сократить 15 тулов до ~11, проще агенту; CLI-поверхность не трогаем) ✅

      (например, `tools()` MCP vs реальные туллы — как `preview`/`verify`)

### 29.2. Внедрение навыков (идей) в команды
По каждой команде — модернизация с идеями из `docs/ideas-audit-2026.md`:

- [ ] [fact] `inspect`/`search_schema` — расширить на документы/регистры/синонимы ✅
      (идея 1CDBStorageStructureInfo: двунаправленный поиск)
      и техжурнал-источник (Фаза 26) как опцию --source-type
- [x] [fact] **Селективный перенос по разделам** (требование пользователя):
      `extract --objects "Справочник.Номенклатура,Документ.БанковскиеВыписки"` —
      фильтр по конфигурационным объектам (kind+имя из read_metadata), а не по
      физическим таблицам; поддержка групп `Справочник.*`/`Документ.*`/`Регистр.*`;
      без --objects — перенос ВСЕХ данных (по умолчанию); MCP `step_extract`
      — параметр `objects`; список доступных разделов — через `inspect`
      и техжурнал-источник (Фаза 26) как опцию --source-type ✅
- [ ] [fact] `map`/`transform` — экспорт правил TOON в XML КД3 (`export-kd3`, ✅
      идея ConversionRulesLoader); fuzzy-подсказка полей (идея OpenIntegrations)
- [ ] [fact] `load`/`load_direct` — OAuth2/JWT (Фаза 22), snapshot (Фаза 24), ✅
      audit-лог (Фаза 25), Telegram-уведомление (Фаза 27) — флаги/конфиг
- [ ] [fact] `query`/`query_sql` — health-тул базы (Фаза 27) рядом; добавить ✅
      EXPLAIN-подобный вывод плана (идея consquery/RequestConsole9000)
- [ ] [fact] `guid-diff`/`config-versions` — анализ модулей/расширений ✅
      (идеи bsl-parser/diff3cf): дифф по модулям конфигурации
- [ ] [fact] `doctor` — расширить диагностику: OAuth2-конфиг, S3, место под кеш ✅
      (порог), версия платформы если доступна (v8runner)
- [ ] [fact] `cache` — TTL/лимит размера (идея: бесконтрольный рост), авто-очистка ✅
      старых; stats показывает возраст
- [ ] [fact] `dump-records` — формат csv: quoting/разделители (идея: читаемость), ✅
      опция --where (фильтр как в query)
- [ ] [fact] `metrics` — pushgateway-режим и APDEX (идея 1C_PrometheusExporter); ✅
      метрики строк/сек и ошибок
- [ ] [fact] `migrate` (MCP) — обновить next-цепочку под новые туллы ✅
      (base_health, export-kd3); прогресс-события
- [ ] [fact] `dump_metadata` — git-совместимый дифф (идея GitConverter): вывод ✅
      построчный, стабильный порядок для чистых git-диффов

### 29.3. Тесты и верификация взаимосвязей
- [ ] [fact] Тест карты команд: каждая CLI-команда имеет --help и handler; ✅
      каждый MCP-тул зарегистрирован и вызывается (smoke)
- [ ] [fact] Сквозной e2e по цепочке команд (inspect→extract→map→transform→load) ✅
      на синтетике — подтверждает согласованность аргументов и данных
- [ ] [assumption] docs/commands-map.md + README: сводная таблица команд, ✅
      их связей и внедрённых навыков
- [ ] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные ✅

---

---

## Фаза 30 — Регрессии анализа (закрыты) + защита от повторений

Регрессии из повторного анализа (исправлены в hotfix `1fe673c`):
- [x] [fact] Module.bsl: возвращено `ЗаписьДанных(Запрос) Экспорт` (дубль НайтиОбъект2 + необъявленный Запрос) — модуль компилируется
- [x] [fact] Dockerfile: install после COPY src (+LICENSE/README) — образ собирается
- [x] [fact] anonymizer: `_FIO_RE` только 3 слова с заглавной — произвольные фразы не портятся
- [x] [fact] CLI load: `--api-key`/`--retries` (проброс в HttpClient83, конфиг)

Защита от повторений (автопроверка вне периметра pytest):
- [ ] [fact] CI: шаг `docker build .` (ловит регрессии Dockerfile)
- [ ] [fact] CI: шаг `python -m build && twine check` на каждый push (сборка пакета)
- [ ] [fact] статическая проверка .bsl: скрипт `scripts/check_bsl.py` — дубли
      `Функция <имя>(` в одном модуле + необъявленные параметры
- [ ] [fact] единый источник версии: `version = {attr = "onec_converter.__version__"}`
      в pyproject (одна строка в `__init__.py` вместо 3 мест: pyproject/cli/тесты)

## Фаза 31 — Качество и DX из анализа (новые задачи) — ✅ выполнена

- [ ] [fact] CLI `load --http` + конфиг: документировать `ОжидаемыйКлюч`/`--api-key`
      в extension_83/README.md и корневом README (реальный сценарий)
- [ ] [fact] Module.bsl: нормализация значений перед НайтиПоКоду/Наименованию
      (trim, регистр) — replace не создаёт дубли
- [ ] [fact] cache: TTL/лимит размера с авто-эвикцией (LRU) — stats уже есть,
      добавить `Cache.trim(max_bytes)` и вызов при put
- [ ] [fact] fuzz-тест anonymizer (hypothesis или собственный генератор):
      случайные строки → не изменяются, если не похожи на ФИО/телефон/ИНН
- [ ] [fact] `doctor` расширить: проверка «Module.bsl синтаксически валиден»
      и «пакет собирается» (docker/build)
- [ ] [assumption] README: раздел «Известные ограничения текущего релиза»
      (индексы, data_page=0, серверные базы, 1Cv8.dt)
- [ ] [assumption] CHANGELOG: раздел «0.2.0» актуализировать (фиксы регрессий)

---

---

# Фазы 32+ — план по итогам внешнего анализа v0.14.0 (проверено, август 2026)

Вердикт по анализам: 3 регрессии раунда 2 исправлены (Module.bsl/Dockerfile/
anonymizer ✅); находки раунда 3 подтверждены кодом (clone_db, base_health,
JWT-разрыв, openapi, check_bsl в gates). Устарело из раунда 1: doctor уже есть,
стриминг JSON частично есть (CLI extract — НЕ стриминговый — баг). Каждая
фаза = релиз 0.x.0 (SemVer монотонно).

## Фаза 32 — Дефекты по итогам анализа (0.15.0)

- [x] [fact] clone_db: вычислять file_key(dst) ДО shutil.copy2 и дропать
      именно старый ключ; тест повторного клонирования в существующий
      target_dir с закешированными метаданными
- [x] [fact] base_health: include_rows=False по умолчанию + sample_tables=N —
      health-пинг не должен читать данные всех таблиц
- [x] [fact] check_bsl.py — цель scripts/gates.sh (паритет с ci.yml)
- [x] [fact] audit: один открытый handle + periodic flush; ротация JSONL
      по размеру
- [x] [fact] notify: retry с backoff (webhook/telegram), тест
- [x] [fact] openapi: securitySchemes bearerAuth + тест соответствия
      спеки реальным путям (/metadata, /load)
- [x] [fact] CLI extract: переход на save_json_stream (закрыть OOM-риск
      на больших базах); тест потока
- [x] [fact] Module.bsl: БезопасноеСравнение для X-API-Key
- [x] [fact] cache: тест, что TTL применяется в get/has
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные;
      релиз 0.15.0

## Фаза 33 — JWT-контур целиком (0.16.0)

- [x] [fact] CLI mint-token: выпуск Bearer-токена на общем секрете
      (jwt_auth.mint_jwt) — `onec-converter mint-token --secret ...`
- [x] [fact] http_client: режим mint-token (--secret) для `load --http`,
      тест прохождения токена в Authorization
- [x] [fact] openapi: bearerAuth-схема документирована
- [x] [fact] extension_83/README + README: token_url — внешний OAuth2-сервер
      (не входит в поставку), mint-token — локальный режим
- [x] [fact] тест согласования mint_jwt ↔ ПроверитьJWT (эталонный вектор
      HMAC-SHA256)
- [x] [assumption] ворота зелёные; релиз 0.16.0

## Фаза 34 — Производительность ядра (0.17.0)

- [x] [spike] mmap: уже реализован (source_8x_file self._mm, read_page — срез
      памяти); подтверждено, доп. работ не требует
- [x] [fact] table_stats: кеширован и читает только данные (не blob) через
      mmap — дешёво; base_health sample_tables по row_length (Фаза 32)
- [x] [fact] index_rebuilder.py + load --direct --index-repair: генерация
      скрипта восстановления индексов (chdbfl/1cv8) для приёмника
- [x] [fact] extract --workers: параллельное чтение независимых таблиц
      (ThreadPoolExecutor, порядок сохранён, детерминизм тестом)
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные;
      релиз 0.17.0
## Фаза 35 — Регистры и перечисления (0.18.0)

- [x] [fact] writer регистров сведений (_InfoRg) и накопления (_AccumRg)
- [x] [fact] enum_mapper: авто-маппинг перечислений по внутренним именам
      (не только индексам)
- [x] [fact] map/transform: секция enums в rules.json; CLI-флаги
- [x] [fact] рецепт «перенос остатков» (docs/recipes/)
- [x] [assumption] ворота зелёные; релиз 0.18.0

## Фаза 36 — SQL-источники (0.19.0)

- [x] [fact] sql_source.py: SqlSource (list_tables/fetch_metadata/fetch_rows),
      GenericSqlSource, build_sql_source, SqlSourceError
- [x] [fact] extract --source-kind 1cd|postgres|mssql + --source-url
- [x] [fact] адаптеры: ленивый импорт psycopg2/pyodbc; таблицы _Reference*
      _Document* _InfoRg* _AccumRg* _Enum* через information_schema
- [x] [fact] tests +5 на mock-драйвере; README — SQL-источники
- [x] [assumption] ворота зелёные; релиз 0.19.0
## Фаза 37 — Безопасность и комплаенс (0.20.0)

- [x] [fact] pii_scanner.py: ИНН/СНИЛС/карты/тел (RU+UZ)/ПИНФЛ/e-mail;
      scan_text/scan_record/field_is_pii; профиль UZ
- [x] [fact] audit: tamper-evident (SHA-256 hash-цепочка + verify_audit);
      pii_masking (скрытие ПДн в obj/detail/guid)
- [x] [fact] gdpr_152_report.py + CLI pii-report
- [x] [fact] rbac_mcp: ONEC_MCP_ROLE, load_direct требует load
- [x] [assumption] ворота зелёные; релиз 0.20.0
## Фаза 38 — Мониторинг и DevOps (0.21.0)

- [x] [fact] progress.py + metrics: строки/объекты/ошибки/скорость в Prometheus
- [x] [fact] s3 multipart_upload (create/parts/complete/abort, SigV4)
- [x] [fact] gates.sh цель docker (опц.); ci.yml docker run smoke
- [x] [fact] docker-compose.yml (onec-converter + MinIO)
- [x] [fact] nightly-bench workflow + scripts/benchmark.py
- [x] [assumption] ворота зелёные; релиз 0.21.0
## Фаза 39 — DX и продукт (0.22.0)

- [x] [fact] load --dry-run: план без записи/отправки; тест
- [x] [fact] shell --source-dir: REPL (tables/describe/query/help); тесты
- [x] [fact] Makefile (lint/type/test/bdd/gates/bench)
- [x] [fact] pre-commit hook: блок 1CD/dump/jsonl в коммитах
- [x] [fact] README: «Быстрый старт за 5 минут», бейдж PyPI
- [x] [assumption] ворота зелёные; релиз 0.22.0
## Фаза 40 — AI-навыки (0.23.0)

- [x] [fact] MCP auto_map_schemas: авто-маппинг по именам/синонимам -> rules
- [x] [fact] MCP explain_diff: человекочитаемые причины расхождений
- [x] [fact] ai_skills.compress_metadata: саммари метаданных для LLM
- [x] [fact] examples/: autonomous_migration + context_compressor
- [x] [assumption] ворота зелёные; релиз 0.23.0

# Фазы 41+ — план по итогам раунда 4 внешнего анализа v0.23.0 (проверено, август 2026)

## Фаза 41 — Хирургические дефекты раунда 4 (0.24.0)

- [x] [fact] gen_openapi.py: версия из onec_converter.__version__ (не литерал)
- [x] [fact] gen_openapi.py: BearerAuth для /metadata и /load (везде, где ПроверитьКлюч)
- [x] [fact] audit._rotate(): маркер-запись {"marker":"rotated","prev_hash":...} первой строкой
- [x] [fact] verify_audit(): валидация prev_hash первой записи (пуст для файла без предыстории)
- [x] [fact] sql_source: whitelist-валидация table в fetch_rows + параметризация; скобки в WHERE MSSQL
- [x] [fact] тесты: openapi version==__version__; golden-тест ротации; verify_audit сценарий «ротация→первая запись»; sql-инъекция
- [x] [assumption] ворота зелёные; релиз 0.24.0
## Фаза 42 — Укрепление аудита/комплаенс (0.25.0)

- [x] [fact] verify_audit(cross_files=True): сверка цепочки audit.jsonl + .1 + ...
- [x] [fact] _last_record_hash: кеш при открытии (не читать весь файл каждый раз)
- [x] [fact] pii_masking=True по умолчанию (opt-out) + changelog-запись о разнице
- [x] [fact] crypto_utils.py: общий sha256/hex/hmac (audit, s3_client, anonymizer)
- [x] [fact] hypothesis: мутация байта в случайной записи ВСЕГДА детектируется verify_audit
- [x] [fact] CLI audit-verify --audit-file; доки: формула hash/prev_hash
- [x] [assumption] ворота зелёные; релиз 0.25.0
## Фаза 43 — SQL-источники до production-grade (0.26.0)

- [x] [fact] _connect(): connect_timeout (не зависать на недоступном сервере)
- [x] [fact] fetch_rows(): потоковая выборка (fetchmany/server-side cursor) вместо fetchall
- [x] [fact] README «SQL-источники: ограничения» + honest contract в docs/openapi.yaml
- [x] [fact] интеграционный тест PostgreSQL в Docker (реальная СУБД) в CI
- [x] [fact] col_sql fetch_metadata: скобки/экранирование (AND/OR приоритет)
- [x] [assumption] ворота зелёные; релиз 0.26.0
## Фаза 44 — Покрытие и качество (0.27.0)

- [x] [fact] COVERAGE_MODULES в pyproject.toml; расширить на audit/clone_db/health/s3_client/sql_source/ai_skills
- [x] [fact] mypy --strict на scripts/ (gen_openapi, gates-хелперы)
- [x] [fact] решение по mypy tests/ задокументировано (README/RELEASING)
- [x] [fact] PII_PROFILES: профиль Узбекистан (ИНН/ПИНФЛ) + тесты
- [x] [fact] gates.sh: тайминг прогона + предупреждение при превышении лимита
- [x] [fact] check_bsl: тест на несколько .bsl-файлов
- [x] [assumption] ворота зелёные; релиз 0.27.0
## Фаза 45 — AI-навыки: глубина и CLI (0.28.0)

- [x] [fact] compress_metadata: save-to-file (out_path)
- [x] [fact] confidence (exact/synonym) в auto_map_schemas
- [x] [fact] CLI ai-map/ai-explain (обёртки MCP-тулов; реестр 26)
- [x] [fact] mint-token --dry-run (payload до подписи) и --json
- [x] [fact] rate-limit в Module.bsl ПроверитьКлюч (блок после 5 неудач)
- [x] [assumption] ворота зелёные; релиз 0.28.0
## Фаза 46 — Продукт и документация (0.29.0)

- [x] [fact] README «tamper-evident audit log» для комплаенс
- [x] [fact] feature matrix (7.7 / файловая 8.x / SQL 8.x)
- [x] [fact] пример диалога Claude/Cursor (auto_map/explain_diff)
- [x] [fact] extension_83/README: Совпадает()/constant-time + rate-limit
- [x] [fact] base_health.errors — реальная диагностика (пустой файл, блокировки)
- [x] [fact] notify.telegram_url + urllib.parse.quote
- [x] [fact] clone_db прогресс-логирование (progress.py, stderr)
- [x] [fact] docs/recipes полный цикл clone-db→load→verify→audit→verify_audit
- [x] [assumption] ворота зелёные; релиз 0.29.0
## Фаза 47 — Архитектурные хвосты (0.30.0, финальная из раунда 4)

- [x] [fact] OnecConverterError базовый класс (clone/sql/health наследуют;
      audit осознанно без доменной ошибки — валидация уровня ValueError)
- [x] [fact] лимит попыток OAuth2 в _ensure_token (max_token_attempts, 5)
- [x] [fact] потокобезопасность cache.py (RLock) + concurrent-тест (8 потоков)
- [x] [fact] понятная ошибка read_metadata на битых файлах (путь+причина)
- [x] [fact] эвикция/лимит _blob_cache (64 МБ, полный сброс при переполнении)
- [x] [fact] секция Security в CHANGELOG
- [x] [assumption] ворота зелёные; релиз 0.30.0

## Итог раунда 4 внешнего анализа (Фазы 41-47, релизы 0.24.0-0.30.0)

Все 5 первоначальных находок и подтверждённые пункты второго анализа
закрыты; оставшееся (delta-миграция, thread-безопасность — реализована,
_oAuth2 — реализовано) — в бэклог ниже. План раунда 4 выполнен полностью.

## Раунд 5 внешнего анализа (v0.30.0) — 62 улучшения, план «Фазы 48-53»

Свежий аудит после Фаз 41-47. Все пункты проверены по коду; реальные
дефекты помечены [bug], остальное — функциональные и продуктовые пробелы.
Нумерация сквозная (U1..U62) для трассировки в задачах фаз.

### A. Реальные дефекты и несогласованности (проверены по коду)
- [bug] U1. CLI-команды `verify` НЕТ, хотя `verify.py` есть и README +
  `docs/recipes/полный-цикл-clone-load-verify-audit.md` (Фаза 46) вызывают
  `onec-converter verify` — описанный сценарий невыполним из CLI.
- [bug] U2. `cache` CLI выставляет только stats/clear; LRU-эвикция
  `Cache.trim(max_bytes, ttl)` (Фаза 18) не доступна — кеш на длинных
  прогонах растёт без лимита.
- [bug] U3. MCP-тулы без таймаута: base_health/table_sizes/
  compare_structures читают гигабайтные базы без asyncio.timeout —
  LLM-агент может зависнуть навсегда.
- [bug] U4. `v77_reader.py:129 read_bytes()` — весь 7.7-файл (до ~2 ГБ)
  загружается в память; риск OOM на больших базах.
- [bug] U5. `cli.py:477` S3-загрузка `f.read_bytes()` — весь файл в память
  перед подписанным PUT.
- [bug] U6. 9 модулей вне COVERAGE_MODULES и без dedicated-тестов:
  kd3_export, sonar_report, gdpr_152_report, source_techlog, notify,
  s3_client, terminal, strict, type_priority — их покрытие 0% невидимо
  для ворот.
- [bug] U7. `notify.send_webhook` молча глотает сетевые ошибки
  (best-effort без stderr/счётчика) — провал уведомления не виден.
- [bug] U8. `extract --source-url` (postgres/mssql DSN) содержит пароль —
  без маскирования попадает в audit-журнал и сообщения об ошибках.

### B. CLI-команды (пробелы)
- U9. Команда `verify` (обёртка verify.py: --source-dir/--target-dir/
  --objects/--sample, --json-отчёт) — закрывает U1.
- U10. `cache trim --max-bytes --ttl` — выставить существующий Cache.trim.
- U11. `export-xlsx` — выгрузка промежуточного JSON в Excel (xlsx_report
  есть, команды нет).
- U12. `map --init` — сгенерировать шаблон rules.json по метаданным
  источника (заготовка для ручной доводки).
- U13. `doctor --fix` — авто-починка: cache trim+clear, проверка путей,
  отсутствующих файлов правил.
- U14. `benchmark` — вынести scripts/benchmark.py в CLI (--tables/
  --iterations/--out).
- U15. `mcp` — запуск MCP-сервера из CLI (сегодня только
  `python -m onec_converter.mcp_server`).
- U16. `list-tables` / `dump-schema` для SQL-источников (таблицы+колонки).
- U17. `audit export-csv` — комплаенс-выгрузка журнала в CSV.
- U18. `rules diff --a --b` — сравнение двух правил TOON.

### C. MCP и LLM-агент (востребованность: интеграции Claude/Cursor)
- U19. MCP-тул `compress_metadata` (ai_skills.compress_metadata есть, тула
  нет) — саммари структур для контекста агента.
- U20. MCP-тул `audit_verify` — проверка tamper-evident цепочки из агента.
- U21. asyncio.timeout на все read-тулы (см. U3).
- U22. MCP-тул `cache_stats` (размер/возраст кеша) для диагностики агента.
- U23. Роль ONEC_MCP_ROLE=inspect: фильтровать write-тулы из списка tools
  (сейчас — только ошибка при вызове).
- U24. Progress-стриминг migrate (ServerSession.notification) — агент видит
  прогресс, а не молчание на гигабайтах.
- U25. auto_map_schemas: фильтр `--objects` (только выбранные объекты).
- U26. Дополнить examples/llm_agent_dialog.md сценарием audit_verify +
  compress_metadata.

### D. Безопасность (востребованность: комплаенс 152-ФЗ/152-УЗ)
- U27. Маскирование секретов в DSN/URL в логах, audit-журнале, ошибках
  (pwd=***/token=***) — закрывает U8.
- U28. s3_client: конфигурируемый region (сейчас us-east-1 по умолчанию),
  опциональный STS/refresh-токен.
- U29. BSL: заголовок Idempotency-Key — вторая линия защиты от дублей
  при сетевых повторах (помимо поиска по ключу).
- U30. JWT: поддержка kid/ротация секрета в ПроверитьJWT (смена ключа
  без простоя).
- U31. Pre-commit секрет-сканер (свой, на rg: CHANGE-ME/AWS-ключи/токены)
  — ловит секреты до коммита.
- U32. BSL: лимит размера пакета (параметр, отказ >1 МБ) — защита от
  переполнения приёмника.
- U33. notify: ретраи и сигнал ошибки наружу (stderr/возврат) — закрывает U7.
- U34. verify --json (машиночитаемый отчёт для CI/комплаенс).

### E. Производительность и память
- U35. v77_reader: потоковое чтение секций (чанки/mmap) вместо read_bytes —
  закрывает U4.
- U36. s3 upload: потоковая загрузка без полного read в память —
  закрывает U5.
- U37. table_stats: один проход по файлу для всех таблиц (сейчас N
  проходов с кешем, Фаза 27) — ускорение оценки объёма переноса.
- U38. guid_diff: инкрементальное сравнение чанками вместо полной загрузки.
- U39. read_metadata: in-memory LRU поверх дискового кеша для MCP-сессии.
- U40. dump-records: потоковый вывод CSV + --max-bytes.
- U41. extract --workers: пул по ключам + потоковая запись промежуточного
  файла (intermediate уже стримится в load — выровнять extract).
- U42. cache: атомарная запись tmp+rename — защита от частичных артефактов
  при крахе процесса.

### F. Тесты и качество
- U43. Расширить COVERAGE_MODULES на 9 модулей U6.
- U44. Dedicated-тесты: notify (retry/telegram), s3 (sign_v4 golden),
  kd3 (XML round-trip), sonar (xml/json), gdpr (отчёт), techlog (парсинг),
  terminal (видимость), strict (границы), type_priority.
- U45. Контракт-тест «каждая команда docs/commands-map.md существует в
  CLI» — ловит дрейф типа U1 навсегда.
- U46. Тесты verify-команды (после U9).
- U47. Property-тест round-trip 1CD запись→чтение (границы полей).
- U48. Windows CI-джоба (pytest+vitest) — проект Windows-центричен,
  CI на ubuntu-latest.
- U49. Бенчмарк-пороги: максимальное время критичных тестов (extract/load)
  в воротах — ловит регрессии скорости.
- U50. Fuzz расширение: hypothesis для cache-путей и sql_source whitelist.

### G. Продукт и востребованность
- U51. README: матрица 26 команд с примерами (самогенерируемая из --help
  в CI).
- U52. docs/format-8x.md: описание формата 1CD (таблицы/индексы/строки) —
  доверие и контрибьюторы.
- U53. Пример сквозной миграции «Бухгалтерия 7.7 → 8.3» (v77 читается,
  сценария нет).
- U54. Раздел «приёмник в облаке/1С:Фреш» — как подключить HTTP-расширение
  к облачным ИБ.
- U55. CLI `pii-report` — расширить полями gdpr_152_report (модуль есть,
  команда частично переиспользует; выставить все отчёты).
- U56. Команда `stats` (объекты/реквизиты/таблицы из read_metadata) —
  оценка объёма миграции до переноса.
- U57. Двуязычный help (--help eng/ru) — привлекательность open-source.
- U58. CI на pull_request — отдельная быстрая smoke-джоба
  (pytest core + ruff).
- U59. Плагины/хуки extract/transform/load — точки расширения для
  пользовательских конвертаций.
- U60. Typed-конфиг: dataclass-секции вместо ручного парсинга toml.
- U61. Ошибки с контекстом: path/op/table в OnecConverterError.
- U62. Версионирование правил TOON (schema_version + миграции).

### План «Фазы 48-53» (релизы 0.31.0-0.36.0)

Порядок: сначала связность CLI↔доки и доверие (U1/U9 — блокер сценария),
затем память (риск OOM), затем покрытие (невидимое 0%), затем MCP-агент
(востребованность), затем безопасность (комплаенс), затем продукт.

## Фаза 48 — Связность CLI↔доки и доверие (0.31.0)

- [ ] [fact] CLI `verify` (U1/U9): --source-dir/--target-dir/--objects/--sample,
      --json-отчёт; README-рецепт полного цикла обновляется на реальную команду
- [ ] [fact] `cache trim --max-bytes/--ttl` (U2/U10) + тесты LRU-эвикции через CLI
- [ ] [fact] `audit export-csv` (U17) — комплаенс-выгрузка журнала
- [ ] [fact] `rules diff --a --b` (U18) — сравнение правил TOON
- [ ] [fact] контракт-тест docs/commands-map.md ↔ CLI (U45) — дрейф ловится в воротах
- [ ] [fact] тесты verify-команды (U46)
- [ ] [assumption] ворота зелёные; релиз 0.31.0

## Фаза 49 — Память и потоковость (0.32.0)

- [ ] [fact] v77_reader потоковое чтение секций (U35, закрывает U4)
- [ ] [fact] s3 upload потоковой загрузкой (U36, закрывает U5)
- [ ] [fact] table_stats одним проходом по файлу (U37)
- [ ] [fact] guid_diff инкрементально чанками (U38)
- [ ] [fact] read_metadata in-memory LRU для MCP-сессии (U39)
- [ ] [fact] dump-records потоковый CSV + --max-bytes (U40)
- [ ] [fact] cache: атомарная запись tmp+rename (U42)
- [ ] [assumption] ворота зелёные; релиз 0.32.0

## Фаза 50 — Покрытие и тесты (0.33.0)

- [ ] [fact] COVERAGE_MODULES + 9 модулей (U43); порог контроля покрытия
- [ ] [fact] dedicated-тесты: notify/s3/kd3/sonar/gdpr/techlog/terminal/
      strict/type_priority (U44)
- [ ] [fact] property-тест round-trip 1CD запись→чтение (U47)
- [ ] [fact] fuzz: hypothesis для cache и sql_source (U50)
- [ ] [fact] бенчмарк-пороги в gates (U49): лимит времени критичных тестов
- [ ] [fact] Windows CI-джоба pytest+vitest (U48)
- [ ] [assumption] ворота зелёные; релиз 0.33.0

## Фаза 51 — MCP и LLM-агент (0.34.0)

- [ ] [fact] asyncio.timeout на read-тулы MCP (U21, закрывает U3)
- [ ] [fact] MCP-тулы compress_metadata и audit_verify (U19/U20)
- [ ] [fact] MCP-тул cache_stats (U22)
- [ ] [fact] ONEC_MCP_ROLE=inspect фильтрует write-тулы из списка tools (U23)
- [ ] [fact] progress-стриминг migrate (U24)
- [ ] [fact] auto_map_schemas --objects фильтр (U25); диалог-пример обновлён (U26)
- [ ] [assumption] ворота зелёные; релиз 0.34.0

## Фаза 52 — Безопасность (0.35.0)

- [ ] [fact] маскирование секретов DSN/URL в логах и аудите (U27, закрывает U8)
- [ ] [fact] s3_client: конфигурируемый region + STS (U28)
- [ ] [fact] BSL: Idempotency-Key + лимит размера пакета (U29/U32)
- [ ] [fact] JWT: kid/ротация секрета в ПроверитьJWT (U30)
- [ ] [fact] pre-commit секрет-сканер (U31)
- [ ] [fact] notify: ретраи + сигнал об ошибке (U33); verify --json (U34)
- [ ] [assumption] ворота зелёные; релиз 0.35.0

## Фаза 53 — Продукт и востребованность (0.36.0)

- [ ] [fact] CLI: doctor --fix, benchmark, mcp (U13/U14/U15)
- [ ] [fact] CLI: export-xlsx, map --init, list-tables/dump-schema SQL,
      stats (U11/U12/U16/U56)
- [ ] [fact] README: матрица команд 26 (U51); docs/format-8x.md (U52)
- [ ] [fact] пример «Бухгалтерия 7.7 → 8.3» (U53); раздел облако/1С:Фреш (U54)
- [ ] [fact] pii-report: все отчёты gdpr_152_report (U55)
- [ ] [fact] версионирование правил TOON schema_version (U62)
- [ ] [assumption] ворота зелёные; релиз 0.36.0

### Вне фаз (бэклог после 0.36.0)
U57 (двуязычный help), U58 (smoke-джоба PR), U59 (плагины/хуки),
U60 (typed-конфиг), U61 (ошибки с контекстом).

## Бэклог (опционально, по востребованности)

- [ ] [spike] Rust-ядро (PyO3) для FAT-цепей/zlib/NVC — ускорение 10-20x
- [ ] [spike] web-дашборд (FastAPI + HTMX) для мониторинга переноса
- [ ] [spike] VSCode-расширение: автодополнение MCP-туллов, подсветка rules.json
- [ ] [spike] helm-чарт (Kubernetes Job/CronJob)
- [ ] [spike] encrypt: AES-256 шифрование дампа перед отправкой в облако
