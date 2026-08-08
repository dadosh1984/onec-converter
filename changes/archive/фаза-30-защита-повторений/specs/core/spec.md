# Spec: core

## Purpose
Фаза 30 — защита от повторений (после регрессий Module.bsl/Dockerfile/anonymizer):
единый источник версии, статическая проверка .bsl, CI-гейты сборки.

## Requirements
- [REQ-1] Единый источник версии: `onec_converter.__version__`; pyproject dynamic.
- [REQ-2] `scripts/check_bsl.py` — дубли Функция/Процедура + Экспорт-обработчики.
- [REQ-3] CI: `check_bsl`, `build + twine check`, `docker build` (не ломая gates).
- [REQ-4] Ворота зелёные; релиз 0.30.0 (TestPyPI, PyPI, GitHub Release).
