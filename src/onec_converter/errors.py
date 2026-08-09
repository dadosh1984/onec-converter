"""Базовые ошибки пакета (Фаза 47).

Один предок для доменных ошибок конвертера — чтобы CLI/MCP могли ловить
все ошибки пакета одним `except OnecConverterError` (а не набором
несвязанных классов). Модульные ошибки (audit/clone_db/sql_source/health)
наследуют его, сохраняя свои имена для обратной совместимости.
"""
from __future__ import annotations


class OnecConverterError(Exception):
    """Базовая ошибка onec-converter: все доменные ошибки — его потомки."""
