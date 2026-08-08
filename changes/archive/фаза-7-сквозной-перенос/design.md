# Design — фаза-7-сквозной-перенос

## Overview

Первый полный сценарий переноса данных между ИБ 1С: **7.7 → 8.3**.
Сейчас каждый коннектор (Base77/read_table, intermediate, transform,
HTTP-приёмник) покрыт unit-тестами отдельно — сквозного теста нет.
Фаза связывает их в один путь данных и фиксирует сценарий в MCP
и документации.

## Поток данных

```
Base77 (1Cv77.dat, cp866/cp1251)
   │  step_extract / read_table
   ▼
intermediate JSON  (save_json_batch, UTF-8)
   │  step_map → transform (TOON-правила)
   ▼
target-объекты (transform_object, RefResolver)
   │  validate_batch (количество/ссылки/дубликаты)
   ▼
HTTP-приёмник 8.3 (расширение: POST /load)  ← в тестах — HTTP-mock
```

## Модули

- `mcp_server.py` — шаги пайплайна (step_init/…/step_load) + новый тул
  `migrate(...)` (пошаговый сценарий с прогрессом) — или пошаговые
  вызовы с проверкой `pipeline_status`.
- `tests/test_pipeline_e2e.py` — интеграционные тесты сквозного переноса:
  синтетика 7.7 (gen_dat) → HTTP-mock приёмника (aiohttp/httpx MockTransport).
- `docs/pipeline.md` — потоки данных, форматы батчей, стыковка коннекторов.
- README — раздел «Сквозной перенос 7.7→8.3».

## Решения

- Тестовый приёмник — HTTP-mock (httpx MockTransport): реальные базы 8.3
  не изменяются (read-only), запись тестируется на заглушке.
- Сквозной тест CP1251: gen_dat(encoding='cp1251') → Base77(encoding='cp1251')
  → intermediate → приёмник; проверка, что кириллица дошла без искажений
  (A4 middleware в полном пайплайне).
- MCP-сценарий: `migrate(...)` выполняет шаги последовательно, каждый шаг
  логируется в терминал (▶/✔/✘) и попадает в pipeline_status + timings;
  при ошибке — частичный прогресс и код ошибки.

## Assumptions

- [ ] [spike] Пайплайн end-to-end: потоки данных, форматы батчей,
      стыковка коннекторов; docs/pipeline.md
- [ ] [fact] Интеграционный тест полного переноса на синтетике
      (gen_dat cp866 → TOON → HTTP-mock; количество/ссылки/кодировки)
- [ ] [fact] Сквозной тест CP1251-варианта (A4 middleware)
- [ ] [assumption] MCP-тул `migrate(...)` или пошаговый сценарий
      с pipeline_status + timings
- [ ] [assumption] README «Сквозной перенос 7.7→8.3»

## Verification

- [x] pytest (все тесты, включая интеграционные e2e)
- [x] mypy src (strict)
- [x] ruff check src tests
- [x] npx vitest run (Orion shield)
