# Spec: core

## Purpose
Закрыть подтверждённые кодом дефекты внешнего анализа: неверная инвалидация
кеша clone_db, дорогой base_health, отсутствие check_bsl в gates, per-record
файл в audit, отсутствие retry в notify, openapi без Bearer, OOM в CLI extract,
timing-уязвимость X-API-Key в Module.bsl. Версия 0.15.0.

## Acceptance criteria
- [x] clone_db: file_key(dst) считается до shutil.copy2; дропается именно
      старый ключ (по прежнему файлу приёмника), повторное клонирование
      не отдаёт старые метаданные; тест
- [x] base_health: rows не вычисляется по умолчанию (rows=-1,
      rows_computed=False); include_rows=True и sample_tables=N работают;
      MCP-тул получил include_rows
- [x] check_bsl вызывается целью `bsl` и в `all` gates.sh
- [x] audit: один TextIO handle, flush через file_flush записей,
      close() idempotent, ротация JSONL в .1 при превышении max_bytes
- [x] notify: retry до attempts, экспоненциальный backoff на URLError;
      4xx/5xx не ретраится
- [x] openapi: BearerAuth (http/bearer/JWT) зарегистрирован, /load
      принимает Bearer; тест соответствия путям спеки реальным эндпоинтам
- [x] CLI extract пишет через save_json_stream (валидный JSON-массив,
      без OOM); тест roundtrip
- [x] Module.bsl: constant-time сравнение Функция Совпадает(А, Б)
- [x] Ворота: pytest (+14), conformance, ruff, mypy (43), check_bsl,
      vitest — зелёные; релиз 0.15.0
