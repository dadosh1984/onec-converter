# Spec: read-only-mypy-strict-ruff-pytest-http-m

## Purpose
Фаза 7: сквозной перенос данных 7.7→8.3 (интеграция пайплайна) для MCP-сервера onec_converter (перенос между ИБ 1С, авторский парсер 1Cv8.1CD). Цель: первый полный сценарий переноса — Base77 (7.7, cp866/cp1251) → intermediate JSON → TOON-правила маппинга → transform → validate → загрузка в приёмник 8.3 (HTTP-расширение). Сейчас каждый коннектор тестируется отдельно, сквозного теста нет. Задачи: (1) spike: пайплайн end-to-end — потоки данных, форматы батчей, точка стыковки коннекторов, зафиксировать в docs/pipeline.md; (2) fact: интеграционный тест полного переноса на синтетике (gen_dat 7.7 cp866 → правила TOON → HTTP-mock приёмника 8.3; контроль количества записей, ссылок, кодировок); (3) fact: сквозной тест CP1251-варианта (A4 middleware: cp1251 → UTF-8 до приёмника без искажений); (4) assumption: MCP-сценарий переноса — тул migrate(...) (последовательность шагов пайплайна с прогрессом и timings) или пошаговые вызовы с проверкой pipeline_status; (5) assumption: README раздел «Сквозной перенос 7.7→8.3» с примером команд агенту. Ворота: pytest, mypy strict, ruff, vitest (Orion shield). Реальные базы читаются только read-only, запись — только в тестовый приёмник/HTTP-mock. Python 3.11+, Windows.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
