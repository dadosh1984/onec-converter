# Tasks — фаза-7-сквозной-перенос

Сквозной перенос 7.7→8.3: Base77 (cp866/cp1251) → intermediate JSON → TOON-правила
→ transform → validate → загрузка в приёмник 8.3 (HTTP-mock/расширение).
Первый полный сценарий: каждый коннектор протестирован отдельно, сквозного нет.

- [ ] [spike] Пайплайн end-to-end: потоки данных между шагами
      (init → inspect → extract → map → transform → validate → load),
      форматы батчей, точка стыковки Base77/read_table ↔ intermediate ↔
      HTTP-приёмник; зафиксировать в docs/pipeline.md
- [ ] [fact] Интеграционный тест полного переноса на синтетике:
      gen_dat (7.7, cp866) → правила TOON → HTTP-mock приёмника 8.3;
      контроль количества записей, ссылок, кодировок
- [ ] [fact] Сквозной тест CP1251-варианта: cp1251 → UTF-8 до приёмника
      без искажений (A4 middleware в полном пайплайне)
- [ ] [assumption] MCP-сценарий переноса: тул `migrate(...)` —
      последовательность шагов пайплайна с прогрессом и timings
      (или пошаговые вызовы с проверкой pipeline_status)
- [ ] [assumption] README: раздел «Сквозной перенос 7.7→8.3» с примером
      команд агенту (Claude/Cursor)

Ворота: pytest, mypy strict, ruff, vitest (Orion shield). Реальные базы —
read-only; запись — только в тестовый приёмник (HTTP-mock).
