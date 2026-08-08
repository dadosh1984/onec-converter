# Changelog

Все заметные изменения для пользователя. Формат — по убыванию версий.
Версия — SemVer, монотонно растёт; номер фазы — в описании релиза.

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
