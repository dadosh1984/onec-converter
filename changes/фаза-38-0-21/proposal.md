# Proposal — фаза-38-0-21

**Goal:** Фаза 38 (0.21.0) — Мониторинг и DevOps onec-converter: (1) prometheus-экспорт прогресса переноса: счётчики строк/сек, ошибки, объёмы — дополнить metrics.py процессом (extract/load строк в единицу времени, общее число, счётчики по типу); функция workflow_progress/export_metrics_prometheus; CLI metrics уже есть — расширить выводом; (2) s3_client: multipart upload для больших отчётов (инициализация create_multipart_upload, upload_part, complete_multipart_upload через SigV4); честно — если сложно, документировать и simple put для малых; (3) docker build — опциональная цель gates.sh (простая сборка если docker доступен), docker run smoke в ci.yml; (4) docker-compose.yml пример (onec-converter + MinIO для S3-экспорта); (5) nightly-bench GitHub workflow: бенчмарк времени parse/extract на коммите (через benchmark-скрипт scripts/benchmark.py). Тесты: metrics прогресса (счётчики инкремент), multipart подпись хотя бы структура (мок), nightly/композ не тестируется (конфиг). CHANGELOG 0.21.0, план ✅, релиз.

- Platform: тесты в E:\test через gates.sh; версия 0.21.0; mypy только src; docker-цели gates — опциональные (пропуск без docker)
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b, фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9
