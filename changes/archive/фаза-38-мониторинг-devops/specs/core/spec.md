# Spec: core

## Purpose
Добавить мониторинг прогресса и DevOps-инфраструктуру: Prometheus-метрики
хода переноса, multipart-загрузку в S3 для больших отчётов, docker/gates и
ночной бенчмарк. Версия 0.21.0.

## Acceptance criteria
- [x] progress.py: WorkflowProgress (rows/objects/errors/bytes/rows_per_sec),
      get_progress/reset_progress, render_prometheus соответствует формату
      Prometheus counters/gauge
- [x] cmd_metrics выводит прогресс-метрики (кроме кеша/операций)
- [x] s3_client.multipart_upload: <= chunk -> put_object; иначе
      create_multipart_upload (POST ?uploads), upload_part (PUT
      partNumber&uploadId), complete (POST uploadId, XML), abort при сбое
- [x] gates.sh: цель docker (build, пропуск без docker); ci.yml: docker run
      --rm onec-converter:ci --version (smoke)
- [x] docker-compose.yml: onec-converter + MinIO (S3-экспорт)
- [x] nightly-bench workflow (cron 03:00 + dispatch) + scripts/benchmark.py
      (fake-база, время метаданных/чтения, строк/сек)
- [x] Ворота: pytest (+5), conformance, ruff, mypy (49), check_bsl,
      vitest — зелёные; релиз 0.21.0
