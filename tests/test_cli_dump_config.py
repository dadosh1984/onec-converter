"""Фаза 20: команда dump-records и конфиг-файл."""
from __future__ import annotations

from pathlib import Path

from onec_converter.cli import cmd_dump_records
from onec_converter.config import ProjectConfig
from onec_converter.fake_1cd import FixtureField, FixtureTable, write_fake_1cd


def _base(tmp_path: Path) -> Path:
    base = tmp_path / 'src'
    base.mkdir()
    t = FixtureTable('_REFERENCE1', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=8),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
    ])
    from onec_converter.fake_1cd import encode_row
    t.rows = [encode_row(t.fields, {'_CODE': f'{i:04d}', '_DESCRIPTION': f'Имя{i}'})
              for i in range(5)]
    write_fake_1cd(base / '1Cv8.1CD', [t])
    return base


class _A:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_dump_records_json(tmp_path, capsys):
    base = _base(tmp_path)
    args = _A(source_dir=str(base), table='_REFERENCE1', limit=3, format='json')
    rc = cmd_dump_records(args)
    assert rc == 0
    import json
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 3
    assert rows[0]['_CODE'] == '0000'


def test_dump_records_csv(tmp_path, capsys):
    base = _base(tmp_path)
    args = _A(source_dir=str(base), table='_REFERENCE1', limit=2, format='csv')
    rc = cmd_dump_records(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert '_CODE' in out


def test_config_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = ProjectConfig.load()
    assert c.source_encoding == 'cp866' and c.retries == 3


def test_config_from_file(tmp_path, monkeypatch):
    (tmp_path / 'onec.toml').write_text(
        '[onec]\nsource_encoding = "cp1251"\nretries = 5\nlimit = 10\n',
        encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    c = ProjectConfig.load()
    assert c.source_encoding == 'cp1251'
    assert c.retries == 5
    assert c.limit == 10
