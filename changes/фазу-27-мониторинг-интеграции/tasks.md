# Tasks — Фаза 27: Мониторинг и интеграции (health + S3 + уведомления)

Ворота: mypy strict, ruff, pytest (E:\test, gates.sh), vitest.
Версия 0.12.0. Релиз: TestPyPI → PyPI → GitHub.

## health
- [x] [fact] `base_health(source_dir)`: версия, таблицы/строки, locks
      (1Cv8.1CL/1Cv8tmp*), free_bytes, file_bytes, page_size; HealthError
- [x] [fact] MCP-тул `base_health` (13-й тул) — JSON-ответ, ошибка -> {ok: False}

## S3
- [x] [fact] `sign_v4`: канонический SigV4 (canonical request, string-to-sign,
      HMAC-цепочка) — совпадает с эталоном botocore (5f76a867...)
- [x] [fact] `put_object(bucket, key, data, key/secret/endpoint/region/ct)`:
      path-style URL, env AWS_*; S3Error без ключей/при сетевом сбое
- [x] [fact] CLI `dump-report --file --s3 [--endpoint --key --secret --region]`

## Уведомления
- [x] [fact] `send_webhook` (HTTP POST JSON, best-effort статус),
      `telegram_url`/`notify_telegram`; NotifyError
- [x] [fact] CLI load: `--notify-url` / `--notify-telegram token:chat_id`
      (best-effort, сбой не меняет rc)

## Тесты и доки
- [x] [fact] тесты: health на fake-базе (+lock-файлы, ошибка), SigV4 vs эталон,
      S3-мок (PUT/Authorization/payload), webhook-мок, dump-report без ключей,
      notify (+11)
- [x] [fact] README — «Мониторинг и интеграции»; CHANGELOG 0.12.0;
      план Фаза 27 ✅

## Верификация
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.12.0: TestPyPI → PyPI → GitHub Release
