"""Маркер Фазы 14 (Вариант A): тестовая инфраструктура жива.

Фактические ворота (pytest, ruff, mypy strict, vitest) проверяет shield;
этот файл лишь фиксирует, что тестовая среда проекта работает с новыми
документирующими тестами индекса (read-only, реальная база 8.1).
"""
from __future__ import annotations


def test_phase14_docs_tests_import():
    import importlib
    importlib.import_module("tests.test_8x_index_format")
    importlib.import_module("tests.test_8x_index_warning_preserved")
