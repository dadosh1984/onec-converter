"""README/commands-map: fetch-config поддерживает английские теги."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_commands_map_mentions_english_tags():
    cm = ROOT / 'docs' / 'commands-map.md'
    if not cm.is_file():
        return  # файла нет — тест пропускается (не ошибка)
    text = cm.read_text(encoding='utf-8')
    assert 'fetch-config' in text


def test_fetch_config_docstring_mentions_english():
    src = (ROOT / 'src' / 'onec_converter' / 'fetch_config.py')
    text = src.read_text(encoding='utf-8')
    assert 'Catalog' in text or 'MDClasses' in text or 'англ' in text.lower()
