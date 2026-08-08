# Spec: core

## Purpose
Мониторинг и интеграции (Фаза 27): `base_health` (здоровье базы, MCP-тул),
экспорт отчётов в S3 через авторский минимальный SigV4-клиент
(`dump-report`), уведомления по завершении `load` (webhook/Telegram).
Версия 0.12.0.

## Acceptance criteria
- [x] `base_health(source_dir)`: version, tables, rows (table_stats),
      locks (1Cv8.1CL/1Cv8tmp*), free_bytes, file_bytes, page_size; HealthError
      при отсутствии 1Cv8.1CD; MCP-тул `base_health` (13-й) — JSON;
      ошибка -> {ok: False, error}
- [x] `sign_v4`: canonical request + string-to-sign + HMAC-цепочка AWS SigV4;
      сверено с эталоном клиента botocore S3SigV4Auth (PUT /test%20file.txt,
      Signature=5f76a8670176f81a92f0d44e0c8f1183ff2c686799714737e39a0b65aeec3602)
- [x] `put_object`: path-style URL (default virtual-hosted AWS, endpoint —
      path-style MinIO/Yandex), ключи --key/--secret или AWS_ACCESS_KEY_ID/
      AWS_SECRET_ACCESS_KEY; S3Error без ключей и при URLError
- [x] CLI `dump-report --file --s3 [--endpoint --key --secret --region]`;
      content-type по расширению (json/xlsx); rc=1 с сообщением в stderr
- [x] `send_webhook`: HTTP POST JSON; 4xx/5xx -> {ok: False, status};
      URLError -> NotifyError; `notify_telegram` через telegram_url
      (https://api.telegram.org/bot<token>/sendMessage?chat_id=)
- [x] CLI load: `--notify-url URL` / `--notify-telegram token:chat_id`;
      best-effort — сбой доставки печатается в stderr, rc не меняется
- [x] Тесты (+11): health на fake-базе, lock-файлы, HealthError; SigV4 vs
      эталон; S3-мок (PUT, Authorization AWS4-HMAC-SHA256, payload, path);
      webhook-мок (тело JSON); dump-report без ключей; notify-формат
- [x] README «Мониторинг и интеграции»; CHANGELOG 0.12.0; план Фаза 27 ✅
- [x] Ворота: pytest (все, gates.sh на E:), conformance, ruff, mypy strict,
      vitest — зелёные; релиз 0.12.0 на всех площадках
