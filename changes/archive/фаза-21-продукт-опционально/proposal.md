# Proposal — фаза-21-продукт-опционально

**Goal:** Фаза 21 — продукт (опционально, после стабилизации). Сфокусироваться на реализуемом и ценном: (1) готовый рецепт-сценарий миграции под реальную задачу: docs/recipes/бекас-в-бухгалтерию-3.md — пошаговый перенос BEKAS PLUS BIZNES → Бухгалтерия для Узбекистана 3.0 (реальное доказательство ценности, последовательность команд CLI/MCP, правила маппинга, проверка); (2) Docker-образ: Dockerfile + .dockerignore (python, зависимости, скрипт-вход для CLI/MCP-сервера), быстрый запуск; (3) подготовка к PyPI: обновить pyproject (авторы, репозиторий, классификаторы, keywords, long_description из README), README-позиционирование «чем отличается от onec_dtools/tool1cd»; (4) метрики (Prometheus-формат): простая функция вывода метрик производительности (строк/сек, объём, ошибки) — лёгкая, без новых зависимостей, для Grafana; (5) CHANGELOG/README бейджи уже есть. Веб-UI/Claude Skill — вне объёма (не обязательны для продукта), задокументировать как не-взятое. Реализовать авторским кодом; не ломать pip install и ворота. — Python (pyproject, Dockerfile, .dockerignore, docs/recipes, README, метрики)

- Platform: Философия: без копирования. Ворота: mypy strict, ruff, pytest. Запись только в копии. Docker/PyPI — конфигурация, не ломать установку (mcp pin).
- Constraints: high
- Budget: high
- **Lessons applied (v0.12):** mcp-python-1-7:forge:01528e6c32f6, фаза-7-сквозной-перенос:shield:be4adfcf0907, фаза-8-xlsx-отчёты:shield:2aa0eefd02e7, mcp-python-1-7:forge:8518cd4a492d, migrate-tool-e2e-pipeline:shield:2547efbb2c08
