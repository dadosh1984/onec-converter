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

