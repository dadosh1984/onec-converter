"""Тест entry-point CLI: python -m onec_converter.cli (Фаза 9)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_python_m_cli_help():
    """python -m onec_converter.cli --help → exit 0, подкоманды в выводе."""
    env = {'PYTHONPATH': str(Path('src').resolve())}
    proc = subprocess.run(
        [sys.executable, '-m', 'onec_converter.cli', '--help'],
        capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1])
    assert proc.returncode == 0, proc.stderr
    for cmd in ('inspect', 'extract', 'map', 'transform', 'load', 'status'):
        assert cmd in proc.stdout


def test_python_m_cli_version():
    env = {'PYTHONPATH': str(Path('src').resolve())}
    proc = subprocess.run(
        [sys.executable, '-m', 'onec_converter.cli', '--version'],
        capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1])
    assert proc.returncode == 0, proc.stderr
    assert '0.1.0' in proc.stdout
