# Tasks — Фаза 44: покрытие и качество (0.27.0)

## Покрытие
- [x] [fact] COVERAGE_MODULES в pyproject.toml [tool.onec-gates] + расширение на Фазы 32-40
- [x] [fact] CI: шаг pytest --coverage (порог 70%)

## Типизация
- [x] [fact] mypy strict на scripts/ (src + scripts)
- [x] [fact] политика mypy tests/ задокументирована в README

## PII
- [x] [fact] PII_PROFILES: профиль Узбекистан (ПИНФЛ/ИНН) + тесты

## Инфраструктура качества
- [x] [fact] gates.sh: тайминг pytest + PYTEST_TIME_LIMIT
- [x] [fact] check_bsl: тест на несколько .bsl-файлов

## Релиз
- [x] [assumption] ворота зелёные; релиз 0.27.0
