# Proposal — фаза-31-качество-dx

**Goal:** Фаза 31 — качество и DX из анализа. Задачи: (1) cache: TTL/лимит размера с авто-эвикцией (LRU) — Cache.trim(max_bytes, ttl), вызов при put (удаляет старые/неиспользуемые), stats показывает возраст; (2) fuzz-тест anonymizer: собственный генератор случайных строк (без hypothesis) — случайные и длинные строки не изменяются, если не похожи на ФИО/телефон/ИНН по структуре; + тест на обычные фразы («ООО Ромашка Плюс» не портится); (3) Module.bsl: нормализация значений перед НайтиПоКоду/Наименованию (trim пробелов, верхний регистр для сравнения) — replace не создаёт дубли из-за пробелов/регистра; (4) доки: README/extension_83 — как задать ОжидаемыйКлюч/--api-key в реальном сценарии; обновить CHANGELOG (0.4.0). Ворота зелёные; релиз 0.4.0 (TestPyPI/PyPI/GitHub Release) по тегу. — Python (cache.py, anonymizer.py, extension_83/Module.bsl, scripts, docs)

- Platform: Философия: авторский код. Ворота: mypy strict, ruff, pytest. Не ломать существующие тесты cache/anonymizer. TTL/LRU кеша — эвикция не удаляет нужные свежие. fuzz anonymizer — собственный генератор без hypothesis (без новых зависимостей).
- Constraints: high
- Budget: high
- **Lessons applied (v0.12):** фаза-7-сквозной-перенос:shield:be4adfcf0907, фаза-8-xlsx-отчёты:shield:2aa0eefd02e7, migrate-tool-e2e-pipeline:shield:7fa3ad4497fa, mcp-python-1-7:forge:01528e6c32f6, mcp-python-1-7:forge:36a76e92a8be
