"""Контракт CLI bridge-migrate --meta-conflicts."""
from __future__ import annotations

import json

from onec_converter.classify import compare_user_metadata

SRC = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE1',
     'attributes': [
         {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9, 'precision': 0},
         {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string', 'length': 40, 'precision': 0},
     ]},
], 'tables': ['_REFERENCE1']}
TGT_BAD = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE1',
     'attributes': [
         {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9, 'precision': 0},
     ]},
], 'tables': ['_REFERENCE1']}


def test_compare_reports_conflict():
    m = compare_user_metadata(SRC, TGT_BAD)
    c = next(c for c in m['conflict'] if c['name'] == 'Справочник.Контрагенты')
    assert any('Наименование' in d for d in c['diff'])


def test_parser_has_meta_conflicts_flag():
    from onec_converter.cli import build_parser
    p = build_parser()
    assert p.parse_args(['bridge-migrate', '--source-dir', 'src',
                         '--target-dir', 'tgt', '--meta-conflicts'
                         ]).meta_conflicts is True
    assert p.parse_args(['bridge-migrate', '--source-dir', 'src',
                         '--target-dir', 'tgt'
                         ]).meta_conflicts is False


def test_cmd_meta_conflicts_prints_json(monkeypatch, capsys):
    """--meta-conflicts: печатает conflict-отчёт, exit code 1 (есть расхождения)."""
    monkeypatch.setattr('onec_converter.source_8x_file.read_metadata',
                        lambda p: TGT_BAD if 'tgt' in str(p) else SRC)
    from onec_converter import cli as cli_mod

    class A:
        source_dir = 'src'
        target_dir = 'tgt'
        meta_conflicts = True
        workdir = None
        objects = ''
        key = ''
        ignore_cols = ''
        pilot_rows = 3

    rc = cli_mod.cmd_bridge_migrate(A())
    data = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any(c['name'] == 'Справочник.Контрагенты' for c in data['conflict'])
