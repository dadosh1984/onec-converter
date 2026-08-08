# Forge Report — фаза-30-защита-повторений

- **Status:** complete
- **Done:** 8 · **Skipped (cache):** 0 · **Pending:** 0
- **Generated:** 2026-08-08T19:35:23.245Z

| Task | Status |
|------|--------|
| [fact] cli.py `--version` читает `__version__` (import); tests версии — | done |
| [fact] `scripts/release.sh` бампит только `__init__.py` (одна строка) | done |
| [fact] `scripts/check_bsl.py`: дубли Функция/Процедура + обработчики HTTP | done |
| [fact] CI: шаг `python scripts/check_bsl.py` | done |
| [fact] ci.yml: шаг `python -m build + twine check` (python 3.11) | done |
| [fact] ci.yml: шаг `docker build .` (ловит регрессии Dockerfile) | done |
| [assumption] CI зелёный; `docker build` и `build+twine` проходят | done |
| [assumption] релиз 0.30.0: TestPyPI → PyPI → GitHub Release (см. RELEASING.md) | done |


