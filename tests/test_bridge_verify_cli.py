"""Контракт CLI bridge-verify: --key список, --ignore-cols передаются дальше."""
from __future__ import annotations

from types import SimpleNamespace

from onec_converter.cli import build_parser


def test_parser_has_key_and_ignore_cols():
    p = build_parser()
    args = p.parse_args([
        'bridge-verify', '--input', 'bridge.xlsx',
        '--target-dir', 'copydir', '--type', 'Справочник.Банки',
        '--key', 'Код,Наименование', '--ignore-cols', '_VERSION,_MARKED',
    ])
    assert args.key == 'Код,Наименование'
    assert args.ignore_cols == '_VERSION,_MARKED'


def test_parser_defaults():
    p = build_parser()
    args = p.parse_args([
        'bridge-verify', '--input', 'bridge.xlsx',
        '--target-dir', 'copydir',
    ])
    assert args.key == ''
    assert args.ignore_cols == ''


def test_cmd_bridge_verify_passes_args(monkeypatch, capsys):
    import onec_converter.cli as cli_mod
    captured: dict = {}

    def fake_verify(target_dir, copied_dir, obj_fullname, bridge_in, **kw):
        captured.update(kw)
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'diffs': [], 'exported': 1, 'in_rows': 1}

    monkeypatch.setattr('onec_converter.bridge_verify.verify_roundtrip',
                        fake_verify)
    rc = cli_mod.main(['bridge-verify', '--input', 'b.xlsx',
                       '--target-dir', 'dir', '--key', 'Код,Наименование',
                       '--ignore-cols', '_VERSION'])
    assert rc == 0
    assert captured['key_col'] == 'Код,Наименование'
    assert captured['ignore_cols'] == ['_VERSION']
