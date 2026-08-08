# Proposal — довести-прямую-запись-1cd

**Goal:** Довести прямую запись в 1CD до производственной надёжности (Фаза 16). Добавить в load_direct/append_records: (1) верификацию после записи — число строк, чтение без потерь собственным парсером, сверка с источником (verify); (2) лимиты/прерывание — размер батча, открытая ИБ (LockError уже есть), нехватка диска, превышение FAT-слотов — ясные ошибки; (3) атомарность — работа в tmp + атомарный replace, чтобы прерывание не оставляло полузаписанную копию; (4) unit-тесты проверяемой записи (отчёт) и прерывания без полузаписи; (5) интеграционный тест полного цикла 7.7 → … → load_direct → verify «полно 100%»; (6) README/docs — как проверить копию перед использованием. Учесть риск накопления tmp-копий (диск был заполнен): чистить workdir после replace, документировать в docs/zero-setup.md и docs/playbook.md. — Python (onec_converter, load_8x.py, write_8x.py, docs/zero-setup.md, docs/playbook.md)

- Platform: Запись только в копию (copy_1cd, LockError уже есть). Реальные базы read-only. Палитра: verify уже есть (tests/test_verify.py, verify). Учесть tmp-накопление копий (диск C: был заполнен) — workdir-чистка при атомарном replace. Ворота: mypy strict, ruff, pytest, vitest.
- Constraints: high
- Budget: high
- **Lessons applied (v0.12):** фаза-8-xlsx-отчёты:shield:2aa0eefd02e7, фаза-11-новая-порция:forge:537c39f668a9, фаза-11-новая-порция:forge:409e2a92d172, фаза-10-прямая-запись:forge:7b4be40d8e94, mcp-python-1-7:forge:fda2b6c1b70b
