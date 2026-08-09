"""Фаза 56: функциональность (0.39.0).

C1  mcp --stdio/--sse запускает MCP-сервер (раньше только импортировал).
C4  migrate — сквозной перенос одной командой (extract→transform→load).
G2  wizard — интерактивный мастер, --no-run печатает команду.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from onec_converter.cli import build_parser, cmd_mcp, cmd_migrate, cmd_wizard
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd


def _fake_base(tmp_path: Path) -> Path:
    base = tmp_path / 'src'
    base.mkdir(parents=True)
    t = FixtureTable('_REFERENCE1', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=8),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
    ])
    t.rows = [encode_row(t.fields, {'_CODE': f'{i:04d}', '_DESCRIPTION': f'Имя{i}'})
              for i in range(4)]
    write_fake_1cd(base / '1Cv8.1CD', [t])
    return base


def test_migrate_without_rules_writes_json(tmp_path):
    base = _fake_base(tmp_path)
    out = tmp_path / 'out.json'
    args = build_parser().parse_args(
        ['migrate', '--source-dir', str(base), '--out', str(out),
         '--workers', '1'])
    rc = cmd_migrate(args)
    assert rc == 0
    assert out.is_file()
    data = json.loads(out.read_text(encoding='utf-8'))
    assert len(data) == 4


def test_migrate_applies_rules(tmp_path):
    base = _fake_base(tmp_path)
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({
        'version': 1,
        'objects': [{'source': 'Таблица._REFERENCE1', 'target': 'X.Y',
                     'attributes': {'_CODE': '_CODE'}}],
        'enums': {},
    }), encoding='utf-8')
    out = tmp_path / 'out.json'
    args = build_parser().parse_args(
        ['migrate', '--source-dir', str(base), '--rules', str(rules),
         '--out', str(out), '--workers', '1'])
    rc = cmd_migrate(args)
    assert rc == 0
    assert out.is_file()


def test_migrate_missing_source_errors(capsys):
    args = build_parser().parse_args(
        ['migrate', '--source-dir', '/nonexistent-xyz', '--out', '/tmp/x',
         '--workers', '1'])
    assert cmd_migrate(args) == 1
    assert 'источник не каталог' in capsys.readouterr().err


def test_wizard_no_run_prints_command(tmp_path, monkeypatch, capsys):
    base = _fake_base(tmp_path)
    inp = io.StringIO(f"{base}\ncp866\n\n\n{tmp_path}/w.json\n2\n")
    monkeypatch.setattr('sys.stdin', inp)
    args = build_parser().parse_args(['wizard', '--no-run'])
    rc = cmd_wizard(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert '--no-run' in out and 'migrate --source-dir' in out


def test_parser_has_migrate_and_wizard():
    from onec_converter import cli

    cat = cli.COMMAND_CATEGORIES
    assert cat.get('migrate') == 'Перенос' and cat.get('wizard') == 'Перенос'


def test_mcp_stdio_launches_server(tmp_path, monkeypatch):
    """cmd_mcp --stdio вызывает server_main из mcp_server (сервер запускается)."""
    import onec_converter.mcp_server as ms

    called = {}
    monkeypatch.setattr(ms, 'server_main', lambda t: called.setdefault('t', t))
    args = build_parser().parse_args(['mcp', '--stdio'])
    assert cmd_mcp(args) == 0
    assert called.get('t') == 'stdio'
