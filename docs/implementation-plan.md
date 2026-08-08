# План реализации идей (из аудита экосистемы) — фазы 22+

Источник идей: `docs/ideas-audit-2026.md` (200 репо + 6 MCP-конкурентов).
Философия: берём ТОЛЬКО идею, модернизируем (улучшаем) и внедряем
**авторским кодом**. Приоритет: безопасность → зрелость/CI → данные →
производительность → продукт/DX.

---

## Фаза 22 — Безопасность приёмника (OAuth2 + JWT)

Идеи: vladimir-kharin/1c_mcp (OAuth2-прокси), pintov/1c-jwt (HMAC/JWT).

- [ ] [fact] `http_client`: поддержка OAuth2-токена (client-credentials) —
      получение токена + автоматический заголовок; fallback на X-API-Key
- [ ] [fact] `Module.bsl`: проверка Bearer-токена (JWT: подпись HMAC, срок жизни,
      issuer) — заменяет/дополняет shared-secret
- [ ] [fact] конфиг: `onec.toml` — `[auth] token_url/client_id/secret` для приёмника
- [ ] [fact] тесты: получение токена (mock), истёкший/неверный → 401, валидный → 200
- [ ] [assumption] README/docs: раздел «Аутентификация приёмника (OAuth2/JWT)»

## Фаза 23 — Conformance-тесты MCP + CI-гейты

Идеи: DitriXNew/EDT-MCP (E2E/conformance на CI), yukon39/coverage-cli (покрытие).

- [ ] [spike] Что проверяет MCP conformance: список методов (initialize, tools/call,
      resources), транспорт stdio/SSE, формат ошибок → docs/playbook.md
- [ ] [fact] conformance-набор: автотесты нашего mcp_server на соответствие
      (initialize-рукопожатие, tools/list, tools/call, ошибки)
- [ ] [fact] CI: `.github/workflows/ci.yml` — добавить шаг conformance (vitest/pytest)
- [ ] [fact] порог покрытия: `scripts/gates.sh` — опциональный `--coverage` (pytest-cov,
      порог 70% на новые модули)
- [ ] [assumption] README/docs: бейдж coverage + описание conformance

## Фаза 24 — Полный сценарий копии базы (clone-db + rollback)

Идеи: arkuznetsov/cpdb (копирование базы+MSSQL), Tavalik/Perezalivator (перезаливка).

- [ ] [fact] `onec-converter clone-db --source-dir --target-dir`: полная копия
      структуры+данных файловой ИБ в новый каталог (файл-копия + кеш-сброс)
- [ ] [fact] `clone-db --with-rules`: вместе с правилами маппинга (сценарий «стенд»)
- [ ] [fact] снапшот до миграции: `load_direct` — автоматический `workdir/snapshot.1CD`
      до записи; опция `--no-snapshot`
- [ ] [fact] тесты: clone-db на синтетике; snapshot/restore при сбое
- [ ] [assumption] docs/recipes: обновить рецепт — шаг «создать стенд через clone-db»

## Фаза 25 — Audit-логирование миграции

Идеи: oscript-library/logos (log4j-стиль), cpr1c/logosFor1c (сквозное логирование).

- [ ] [fact] `src/onec_converter/audit.py`: лог-записи (уровни INFO/WARN/ERROR;
      время, операция, объект, GUID, правило, результат)
- [ ] [fact] интеграция: `load_direct`/`transform`/`extract` пишут audit-события
      (каждый перенесённый объект: источник→приёмник, правило, время)
- [ ] [fact] CLI `onec-converter audit --file audit.jsonl` — просмотр/фильтр
- [ ] [fact] тесты: audit-файл формируется, содержит GUID/правило/время
- [ ] [assumption] docs: раздел «Аудит переноса (ПДн-соответствие)»

## Фаза 26 — Новые коннекторы: техжурнал 1С + релизы конфигураций

Идеи: Polyplastic/1c-parsing-tech-log (327★), arkuznetsov/yard (релизы).

- [ ] [spike] Формат техжурнала 1С (каталог логов, события, поля) → docs/format-8x.md
- [ ] [fact] `source_techlog.py`: чтение техжурнала как ИСТОЧНИКА (события/метаданные
      операций) — мостик к диагностике миграции
- [ ] [fact] `fetch-config` (идея yard): загрузка релиза конфигурации (из каталога
      поставки/`.cf`) как источника метаданных
- [ ] [fact] тесты: парсинг техжурнала на синтетике; fetch-config на фикстуре
- [ ] [assumption] README/docs: источники «техжурнал», «релиз конфигурации»

## Фаза 27 — Мониторинг и интеграции (health + S3 + уведомления)

Идеи: OneS2Zabbix/ClusterMonitoring (здоровье баз), 1c-s3connector (S3),
Bayselonarrend/OpenIntegrations (MCP-тулы наружу).

- [ ] [fact] MCP-тул `base_health(source_dir)`: число строк/ошибок/блокировки,
      свободное место, версия ИБ — «здоровье базы» для агента
- [ ] [fact] экспорт результатов в S3: `dump-report --s3 <bucket>` (xlsx/json)
      через boto3-подобный клиент (авторский, минимальный)
- [ ] [fact] уведомление по завершении: Telegram-хук (простой HTTP POST) в `load`
- [ ] [fact] тесты: health на синтетике; S3-мок (запись в tmp); webhook-mock
- [ ] [assumption] README/docs: раздел «Мониторинг и интеграции»

## Фаза 28 — DX: BDD-сценарии, Sonar-отчёт, OpenAPI-спека

Идеи: artbear/1bdd (BDD), acc-export/stebi (Sonar), swagger-1c (OpenAPI).

- [ ] [fact] BDD-обёртка сквозных тестов: `given/when/then`-описание сценариев
      миграции (через pytest-фикстуры, без новых зависимостей)
- [ ] [fact] `onec-converter sonar-report`: генерация отчёта lint/ruff в sonar-совместимом
      формате (для CI-интеграции)
- [ ] [fact] `Module.bsl` + `swagger`: статическая OpenAPI-спека приёмника
      (`docs/openapi.yaml`), сгенерированная из кода (скрипт)
- [ ] [fact] тесты: BDD-сценарий проходит; sonar-report валиден (XML/JSON)
- [ ] [assumption] README/docs: раздел «Разработка и качество»

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
реализация (вариант б) → forge → shield → out → коммит/пуш → архивация.
Ворота: mypy strict, ruff, pytest, vitest; тесты в `E:\test`.
