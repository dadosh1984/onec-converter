"""Тесты CLI map: TOON-правила и промпт LLM (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main


def _write_rules(path: Path, rules: dict) -> None:
    path.write_text(json.dumps(rules, ensure_ascii=False), encoding='utf-8')


def test_map_valid_rules(tmp_path: Path, capsys):
    rules = {'version': 1, 'objects': [
        {'source': 'Справочник.1', 'target': 'Справочник.Банки', 'key': ['_code'],
         'attributes': {'_code': 'Код', '_descr': 'Наименование'}}],
        'enums': {}}
    f = tmp_path / 'rules.json'
    _write_rules(f, rules)
    rc = main(['map', '--rules-file', str(f)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True
    assert out['objects'] == 1


def test_map_invalid_rules(tmp_path: Path, capsys):
    # отсутствует 'source' — validate_rules вернёт ошибки
    rules = {'version': 1, 'objects': [
        {'target': 'Справочник.Банки', 'key': ['_code'],
         'attributes': {'_code': 'Код'}}],
        'enums': {}}
    f = tmp_path / 'rules_bad.json'
    _write_rules(f, rules)
    rc = main(['map', '--rules-file', str(f)])
    assert rc == 1
    assert 'правила невалидны' in capsys.readouterr().err


def test_map_missing_rules_file(tmp_path: Path, capsys):
    rc = main(['map', '--rules-file', str(tmp_path / 'nope.json')])
    assert rc == 1


def test_map_llm_prompt(tmp_path: Path):
    ms = tmp_path / 'ms.json'
    mt = tmp_path / 'mt.json'
    out = tmp_path / 'prompt.txt'
    ms.write_text(json.dumps({'objects': [{'name': 'Справочник.1'}]},
                             ensure_ascii=False), encoding='utf-8')
    mt.write_text(json.dumps({'objects': [{'name': 'Справочник.Банки'}]},
                             ensure_ascii=False), encoding='utf-8')
    rc = main(['map', '--llm-prompt', '--meta-source', str(ms),
               '--meta-target', str(mt), '--out', str(out)])
    assert rc == 0
    assert out.is_file()
    assert 'Справочник.1' in out.read_text(encoding='utf-8')