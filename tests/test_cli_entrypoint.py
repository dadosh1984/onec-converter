"""Тест entry-point CLI: python -m onec_converter.cli (Фаза 9)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_python_m_cli_help():
    """python -m onec_converter.cli --help → exit 0, подкоманды в выводе."""
    env = {**os.environ, 'PYTHONPATH': str(Path('src').resolve())}
    proc = subprocess.run(
        [sys.executable, '-m', 'onec_converter.cli', '--help'],
        capture_output=True, encoding='utf-8', errors='replace', env=env,
        check=False, cwd=Path(__file__).resolve().parents[1])
    assert proc.returncode == 0, proc.stderr
    for cmd in ('inspect', 'extract', 'map', 'transform', 'load', 'status'):
        assert cmd in proc.stdout


def test_python_m_cli_version():
    env = {**os.environ, 'PYTHONPATH': str(Path('src').resolve())}
    proc = subprocess.run(
        [sys.executable, '-m', 'onec_converter.cli', '--version'],
        capture_output=True, encoding='utf-8', errors='replace', env=env,
        check=False, cwd=Path(__file__).resolve().parents[1])
    assert proc.returncode == 0, proc.stderr
    from onec_converter import __version__ as _ver
    assert _ver in proc.stdout
