"""Фаза 39: DX и продукт — --dry-run, shell REPL, Makefile, pre-commit."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
from onec_converter.repl import ReplError, parse_command, run_command

F = [FixtureField('_VERSION', 'RV', length=2),
     FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]


def _db(tmp_path: Path) -> Path:
    src = tmp_path / 'src'
    src.mkdir()
    cd = src / '1Cv8.1CD'
    cd.write_bytes(build_fake_1cd([
        FixtureTable('_Reference1', fields=F, rows=[
            encode_row(F, {'_IDRREF': b'\x01' * 16, '_CODE': '00001',
                           '_DESCRIPTION': 'Bank'})])]))
    return src


# ---- --dry-run ----
def test_load_dry_run_no_write(tmp_path: Path, capsys):
    import argparse

    from onec_converter.cli import cmd_load

    batch = tmp_path / 'batch.json'
    batch.write_text(json.dumps([
        {'type': 'Справочник.X', 'id': '1', 'key': [], 'attributes': {},
         'references': {}}]), encoding='utf-8')
    tgt = tmp_path / 'target'
    tgt.mkdir()
    (tgt / '1Cv8.1CD').write_bytes(build_fake_1cd([
        FixtureTable('_Reference2', fields=F, rows=[])]))

    args = argparse.Namespace(input=str(batch), direct=str(tgt), http='',
                              target='', dry_run=True, workdir='',
                              no_snapshot=True, api_key='', token_url='',
                              client_id='', client_secret='', secret='',
                              index_repair=False, notify_url='',
                              notify_telegram='', retries=0, source_ib='s',
                              target_ib='t', audit_file='', pii_masking=False)
    rc = cmd_load(args)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['dry_run'] is True and out['objects'] == 1
    assert out['mode'] == 'direct'


# ---- REPL ----
def test_repl_parse_commands():
    assert parse_command('tables')['cmd'] == 'tables'
    assert parse_command('query _Reference1')['cmd'] == 'query'
    q = parse_command('query _Reference1 WHERE Bank')
    assert q['table'] == '_Reference1' and q['where'] == 'Bank'
    assert parse_command('describe _Reference1')['cmd'] == 'describe'
    assert parse_command('help')['cmd'] == 'help'
    assert parse_command('exit')['cmd'] == 'exit'
    with pytest.raises(ReplError):
        parse_command('nosuch x')


def test_repl_run_command_tables_and_query(tmp_path: Path):
    src = _db(tmp_path)
    out = run_command({'cmd': 'tables'}, src / '1Cv8.1CD')
    assert '_Reference1' in out
    q = run_command({'cmd': 'query', 'table': '_Reference1'}, src / '1Cv8.1CD')
    assert 'Bank' in q
    desc = run_command({'cmd': 'describe', 'table': '_Reference1'},
                       src / '1Cv8.1CD')
    assert '_IDRREF' in desc and 'row=' in desc


# ---- Makefile / pre-commit ----
def test_makefile_has_targets():
    mf = Path('Makefile').read_text(encoding='utf-8')
    for t in ('lint:', 'type:', 'test:', 'bdd:', 'gates:', 'bench:'):
        assert t in mf


def test_precommit_hook_exists():
    hook = Path('.githooks/pre-commit').read_text(encoding='utf-8')
    assert '.1CD' in hook and 'extract.json' in hook
