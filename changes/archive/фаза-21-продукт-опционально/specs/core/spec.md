# Spec: core

## Purpose
Фаза 21 — продукт (опционально): метрики Prometheus, Docker-образ, PyPI-готовность,
готовый рецепт миграции под реальную задачу. Веб-UI/Claude Skill — вне объёма.

## Requirements
- [REQ-1] `src/onec_converter/metrics.py` — рендер метрик Prometheus
  (operation_*, cache_*) без новых зависимостей; CLI `onec-converter metrics`.
- [REQ-2] Dockerfile + .dockerignore; ENTRYPOINT onec-converter.
- [REQ-3] pyproject: version 0.2.0, readme/license/authors/classifiers/keywords/
  urls; README-позиционирование «чем отличается от onec_dtools/tool1cd».
- [REQ-4] Рецепт миграции docs/recipes/бекас-в-бухгалтерию-3.md.
- [REQ-5] Ворота зелёные; не ломать pip install.
