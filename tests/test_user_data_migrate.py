"""README/commands-map: bridge-migrate задокументирован."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_commands_map_mentions_bridge_migrate():
    cm = ROOT / 'docs' / 'commands-map.md'
    if not cm.is_file():
        return
    assert 'bridge-migrate' in cm.read_text(encoding='utf-8')
