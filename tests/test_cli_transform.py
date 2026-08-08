"""Тесты CLI transform: применение правил и dry-run preview (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main
from onec_converter.intermediate import make_object
from onec_converter.mapping import save_rules
from tests.fixtures.gen_dat import make_dat

RULES = {'version': 1, 'objects': [
    {'source': 'Справочник.1', 'target': 'Справочник.Банки', 'key': ['_code'],
     'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}


def test_transform_extract_pipeline(tmp_path: Path):
    """extract (7.7) → transform → out.json с целевыми типами."""
    base = tmp_path / 'base77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    ext = tmp_path / 'extract.json'
    assert main(['extract', '--source-dir', str(base), '--out', str(ext)]) == 0
    rules = tmp_path / 'rules.json'
    save_rules(rules, RULES)
    out = tmp_path / 'transformed.json'
    rc = main(['transform', '--rules-file', str(rules), '--input', str(ext),
               '--out', str(out)])
    assert rc == 0
    objs = json.loads(out.read_text(encoding='utf-8'))
    assert len(objs) == 2
    assert all(o['type'] == 'Справочник.Банки' for o in objs)
    assert objs[0]['attributes']['Наименование'] == 'Товар А'


def test_transform_preview_dry_run(tmp_path: Path, capsys):
    """--preview N: печать первых N строк без записи файла."""
    objs = [
        make_object('Справочник.1', '1|', ['0001', 'Товар А'],
                    {'_code': '0001', '_descr': 'Товар А'}, {}),
        make_object('Справочник.1', '2|', ['0002', 'Товар Б'],
                    {'_code': '0002', '_descr': 'Товар Б'}, {}),
    ]
    inp = tmp_path / 'in.json'
    inp.write_text(json.dumps(objs, ensure_ascii=False), encoding='utf-8')
    rules = tmp_path / 'rules.json'
    save_rules(rules, RULES)
    out = tmp_path / 'never.json'
    rc = main(['transform', '--rules-file', str(rules), '--input', str(inp),
               '--preview', '1'])
    assert rc == 0
    assert not out.exists()
    shown = json.loads(capsys.readouterr().out)
    assert len(shown) == 1
    assert shown[0]['type'] == 'Справочник.Банки'


def test_transform_invalid_rules(tmp_path: Path, capsys):
    inp = tmp_path / 'in.json'
    inp.write_text('[]', encoding='utf-8')
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({'version': 1, 'objects': [{}]}),
                     encoding='utf-8')
    rc = main(['transform', '--rules-file', str(rules), '--input', str(inp),
               '--out', str(tmp_path / 'o.json')])
    assert rc == 1
    assert 'правила невалидны' in capsys.readouterr().err
