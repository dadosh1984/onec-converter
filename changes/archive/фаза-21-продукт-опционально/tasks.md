# Tasks — Фаза 21: продукт (опционально)

Ворота: mypy strict, ruff, pytest, vitest. Авторский код.

## Метрики (Prometheus)
- [x] [fact] `src/onec_converter/metrics.py`: рендер метрик Prometheus
      (operation_*, cache_*) из Timings/Cache; без новых зависимостей
- [x] [fact] CLI `onec-converter metrics` (Prometheus-формат); тест

## Docker
- [x] [fact] Dockerfile (python:3.11-slim, pip install -e .) + .dockerignore;
      ENTRYPOINT onec-converter

## PyPI-готовность
- [x] [fact] pyproject: version 0.2.0, readme=README, license=LICENSE, authors,
      classifiers, keywords, [project.urls] Repository
- [x] [fact] README: раздел «Чем отличается от onec_dtools/tool1cd»

## Рецепт миграции
- [x] [fact] docs/recipes/бекас-в-бухгалтерию-3.md: пошаговый сценарий
      (разведка, правила TOON, extract/transform/load, проверка копии)

## Верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] docs/development-plan.md: Фаза 21 отмечена выполненной;
      веб-UI/Claude Skill — задокументированы как не-взятое
