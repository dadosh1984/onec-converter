# Tasks — Фаза 28: DX (BDD, Sonar, OpenAPI)

Ворота: mypy strict (src), ruff, pytest (E:\test, gates.sh), vitest.
Версия 0.13.0. Релиз: TestPyPI → PyPI → GitHub.

## BDD
- [x] [fact] tests/bdd.py: Step (kind/name/fn), given/when/then, Scenario
      (ctx, steps, run, report, dump), фикстура scenario (conftest.py)
- [x] [fact] tests/test_bdd_scenario.py: сквозной сценарий миграции
      (source → extract → transform → load_direct → verify) + хелперы

## sonar-report
- [x] [fact] sonar_report.py: one_issue (RUF022→RU022; F/E→MAJOR), sonar_report
      (target, xml|json) через ruff --output-format=json; SonarReportError
- [x] [fact] CLI sonar-report: --target/--format/--out

## OpenAPI
- [x] [fact] scripts/gen_openapi.py: пути из http_client.py (_request),
      обработчики из Module.bsl (Экспорт), маппинг path→operation,
      ApiKeyAuth (X-API-Key); docs/openapi.yaml сгенерирован

## Тесты и доки
- [x] [fact] тесты: BDD-сценарий, sonar JSON/XML/ошибки, openapi (+9)
- [x] [fact] README — «Разработка и качество»; CHANGELOG 0.13.0;
      план Фаза 28 ✅

## Верификация
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.13.0: TestPyPI → PyPI → GitHub Release
