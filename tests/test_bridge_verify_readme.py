"""README: раздел bridge-verify описывает нормализацию и --key/--ignore-cols."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_mentions_bridge_verify():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'bridge-verify' in text


def test_readme_mentions_normalize_and_key():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert '--key' in text
    assert '--ignore-cols' in text
