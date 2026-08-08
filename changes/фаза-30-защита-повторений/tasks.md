# Tasks — Фаза 30: защита от повторений

Ворота: mypy strict, ruff, pytest, vitest; тесты в E:\test. Релиз 0.30.0.

## Единый источник версии
- [x] [fact] `src/onec_converter/__init__.py`: `__version__ = "0.2.0"`; pyproject:
      `dynamic=["version"]` + `[tool.setuptools.dynamic] version={attr=...}`
- [x] [fact] cli.py `--version` читает `__version__` (import); tests версии —
      из `onec_converter.__version__` (не tomllib)
- [x] [fact] `scripts/release.sh` бампит только `__init__.py` (одна строка)

## Статическая проверка .bsl
- [x] [fact] `scripts/check_bsl.py`: дубли Функция/Процедура + обработчики HTTP
      обязаны быть Экспорт; exit 1 при проблемах; вход: путь(и) или src/*.bsl
- [x] [fact] CI: шаг `python scripts/check_bsl.py`

## CI-гейты сборки
- [x] [fact] ci.yml: шаг `python -m build + twine check` (python 3.11)
- [x] [fact] ci.yml: шаг `docker build .` (ловит регрессии Dockerfile)
- [x] [assumption] CI зелёный; `docker build` и `build+twine` проходят

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.30.0: TestPyPI → PyPI → GitHub Release (см. RELEASING.md)
