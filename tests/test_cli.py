"""Unit-тесты CLI: парсер, подкоманды, exit-коды (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter.cli import main


def test_help_exit_0(capsys):
    with pytest.raises(SystemExit) as e:
        main(['--help'])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for cmd in ('inspect', 'extract', 'map', 'transform', 'load', 'status'):
        assert cmd in out


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(['--version'])
    assert e.value.code == 0
    assert '0.1.0' in capsys.readouterr().out


def test_unknown_command_exit_2():
    with pytest.raises(SystemExit) as e:
        main(['unknown-cmd'])
    assert e.value.code == 2


def test_inspect_missing_source_exit_1(tmp_path: Path, capsys):
    rc = main(['inspect', '--source-dir', str(tmp_path / 'no_such')])
    assert rc == 1
    assert 'источник не найден' in capsys.readouterr().err


def test_status_json(tmp_path: Path, capsys):
    rc = main(['status', '--project-dir', str(tmp_path)])
    assert rc == 0
    st = json.loads(capsys.readouterr().out)
    assert st['ok'] is True
    assert 'connectors' in st
    assert 'cache' in st