# Tasks — Фаза 38: Мониторинг и DevOps (0.21.0)

## Progress
- [x] [fact] progress.py: WorkflowProgress (строки/объекты/ошибки/скорость);
      metrics выводит Prometheus-метрики прогресса

## S3
- [x] [fact] s3 multipart_upload (create/parts/complete/abort, SigV4);
      <= chunk -> put_object

## CI / Docker
- [x] [fact] gates.sh цель docker (опц.); ci.yml docker run smoke
- [x] [fact] docker-compose.yml (onec-converter + MinIO)

## Nightly
- [x] [fact] nightly-bench workflow + scripts/benchmark.py (fake-база)

## Доки / релиз
- [x] [fact] тесты +5; README мониторинг; CHANGELOG 0.21.0
- [x] [assumption] ворота зелёные; релиз 0.21.0
