"""Фаза 48: связность CLI↔доки — verify, cache trim, audit export-csv,
rules-diff, контракт-тест команд, тесты verify."""
from __future__ import annotations

import json
import re
from pathlib import Path

from onec_converter.cli import cmd_audit, cmd_cache, cmd_rules_diff, cmd_verify


def _mk(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.write_text(content, encoding='utf-8')
    return p


# ---- verify: полное совпадение / расхождения ----
def test_verify_ok_and_mismatch(tmp_path: Path, capsys):
    src = _mk(tmp_path, 'src.json', json.dumps([
        {'type': 'Справочник.Контрагенты', 'key': ['0001'],
         'attributes': {'Наименование': 'ООО Ромашка'}},
        {'type': 'Документ.Продажа', 'key': ['0002'],
         'attributes': {'Сумма': 100}},
    ], ensure_ascii=False))
    tgt_full = _mk(tmp_path, 'tgt_full.json', json.dumps([
        {'type': 'Справочник.Контрагенты', 'key': ['0001'],
         'attributes': {'Наименование': 'ООО Ромашка'}},
        {'type': 'Документ.Продажа', 'key': ['0002'],
         'attributes': {'Сумма': 100}},
    ], ensure_ascii=False))
    tgt_diff = _mk(tmp_path, 'tgt_diff.json', json.dumps([
        {'type': 'Справочник.Контрагенты', 'key': ['0001'],
         'attributes': {'Наименование': 'ДРУГОЕ ИМЯ'}},
    ], ensure_ascii=False))

    import argparse
    ok = cmd_verify(argparse.Namespace(input=str(src), target=str(tgt_full),
                                       objects='', json=True))
    assert ok == 0
    assert json.loads(capsys.readouterr().out)['matched'] == 2

    bad = cmd_verify(argparse.Namespace(input=str(src), target=str(tgt_diff),
                                        objects='', json=True))
    assert bad == 1
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is False
    assert out['missing_total'] == 1
    assert out['mismatched_total'] == 1


def test_verify_objects_filter(tmp_path: Path, capsys):
    src = _mk(tmp_path, 's.json', json.dumps([
        {'type': 'Справочник.Контрагенты', 'key': ['1'],
         'attributes': {}},
        {'type': 'Документ.Продажа', 'key': ['2'], 'attributes': {}},
    ]))
    tgt = _mk(tmp_path, 't.json', json.dumps([
        {'type': 'Справочник.Контрагенты', 'key': ['1'], 'attributes': {}},
    ]))
    import argparse
    # фильтр только на справочники — расхождение по Документу не видно
    rc = cmd_verify(argparse.Namespace(input=str(src), target=str(tgt),
                                       objects='Справочник.*', json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['total_source'] == 1


# ---- cache trim через CLI ----
def test_cache_trim_cli(tmp_path: Path, capsys):
    import argparse
    c = tmp_path / 'cc'
    c.mkdir()
    (c / 'aaa').mkdir()
    (c / 'aaa' / 'f1').write_bytes(b'x' * 1000)

    rc = cmd_cache(argparse.Namespace(root_dir=str(c), sub='trim',
                                      max_bytes=100, ttl=0))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['removed'] >= 1
    assert out['bytes'] == 0


# ---- audit export-csv ----
def test_audit_export_csv(tmp_path: Path, capsys):
    import argparse
    log = _mk(tmp_path, 'a.jsonl',
              '{"ts":"2026-08-01T10:00:00Z","level":"INFO","operation":"load",'
              '"obj":"Справочник.Номенклатура","result":"ok","guid":"","rule":"r"}\n')
    out = tmp_path / 'out.csv'
    rc = cmd_audit(argparse.Namespace(file=str(log), level='', op='', obj='',
                                      tail=0, json=False, csv_out=str(out)))
    assert rc == 0
    txt = out.read_text(encoding='utf-8-sig')
    assert 'ts,level,operation' in txt
    assert 'load' in txt


# ---- rules-diff ----
def test_rules_diff(tmp_path: Path, capsys):
    import argparse
    a = _mk(tmp_path, 'a.json', json.dumps({'version': 1, 'objects': [
        {'source': 'Справочник.А', 'target': 'Справочник.Б',
         'attributes': {'Поле': 'Поле'}}]}, ensure_ascii=False))
    b = _mk(tmp_path, 'b.json', json.dumps({'version': 1, 'objects': [
        {'source': 'Справочник.А', 'target': 'Справочник.Б',
         'attributes': {'Поле': 'Поле2'}},
        {'source': 'Документ.Новый', 'target': 'Документ.Новый2',
         'attributes': {}}]}, ensure_ascii=False))
    rc = cmd_rules_diff(argparse.Namespace(a=str(a), b=str(b), json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['added'] == ['Документ.Новый']
    assert out['changed'] == ['Справочник.А']


# ---- контракт-тест: команды docs/commands-map.md существуют в CLI (U45) ----
def test_commands_map_contract():
    cli_src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    cmds_in_cli = set(re.findall(r"add_parser\('([a-z0-9-]+)'", cli_src))
    mcp_src = Path('src/onec_converter/mcp_server.py').read_text(encoding='utf-8')
    cmds_in_mcp = set(re.findall(r"@visible_tool\('([a-z_]+)'", mcp_src))
    md = Path('docs/commands-map.md').read_text(encoding='utf-8')
    # секция CLI (до MCP-таблицы)
    cli_part = md.split('MCP', 1)[0]
    doc_cli = set(re.findall(r'^\| ([a-z0-9-]+) \|', cli_part, flags=re.MULTILINE))
    missing = {c for c in doc_cli
               if c not in cmds_in_cli and c not in cmds_in_mcp}
    assert not missing, f'команды из commands-map отсутствуют: {missing}'


def test_cli_registry_grows_to_31():
    cli_src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    handlers = re.findall(r"^\s+'([a-z0-9-]+)': cmd_", cli_src, flags=re.MULTILINE)
    parsers = re.findall(r"add_parser\('([a-z0-9-]+)'", cli_src)
    assert len(parsers) == len(handlers) == 31, (len(parsers), len(handlers))


# ---- README-рецепт использует реальную команду verify ----
def test_recipe_uses_verify_command():
    t = Path('docs/recipes/полный-цикл-clone-load-verify-audit.md').read_text(
        encoding='utf-8')
    assert 'onec-converter verify' in t
