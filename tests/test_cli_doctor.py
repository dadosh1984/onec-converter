"""Фаза 17: команда `onec-converter doctor` — диагностика окружения."""
from __future__ import annotations

import pytest

from onec_converter.cli import cmd_doctor


class _A:
    def __init__(self, **kw):
        self.source_dir = ''


def test_doctor_returns_zero_on_healthy(tmp_path, monkeypatch):
    """Типичное окружение (mcp 1.x, PyYAML есть) — doctor возвращает 0."""
    import importlib.metadata as md
    if md.version('mcp').split('.')[0] != '1':
        pytest.skip('mcp не 1.x в этом окружении')
    import yaml  # noqa: F401
    rc = cmd_doctor(_A())
    assert rc == 0


def test_doctor_missing_yaml_does_not_crash(monkeypatch):
    """Нет PyYAML — doctor не падает, возвращает >0 (проблема)."""

    # имитируем отсутствие yaml: блокируем импорт
    class _NoYaml:
        pass

    def fake_import(name, *a, **k):
        raise ModuleNotFoundError(f'No module named {name!r}')

    import builtins
    real = builtins.__import__
    called = []

    def guarded(name, *a, **k):
        if name == 'yaml':
            called.append(name)
            raise ModuleNotFoundError('yaml')
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, '__import__', guarded)
    rc = cmd_doctor(_A())
    assert called == ['yaml']
    assert rc > 0  # yaml отсутствует → проблема


def test_doctor_cli_parser_has_command():
    """Подкоманда `doctor` зарегистрирована в CLI."""
    import argparse

    from onec_converter.cli import build_parser
    p = build_parser()
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert 'doctor' in sub.choices
