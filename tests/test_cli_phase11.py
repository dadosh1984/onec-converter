"""CLI-тесты Фазы 11: query / guid-diff / config-versions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter.cli import main
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.write_8x import create_1cd


def _fields() -> list[FixtureField]:
    return [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
        FixtureField('_QUANTITY', 'N', length=12, precision=2),
    ]


def _base(tmp_path: Path) -> Path:
    rows = [encode_row(_fields(), {'_CODE': '000000001',
                                   '_DESCRIPTION': 'Яблоки', '_QUANTITY': 10.5}),
            encode_row(_fields(), {'_CODE': '000000002',
                                   '_DESCRIPTION': 'Груши', '_QUANTITY': 3.25})]
    p = create_1cd(tmp_path / '1Cv8.1CD',
                   [FixtureTable('_REFERENCE9', fields=_fields(), rows=rows)])
    return p


def test_cli_query(tmp_path: Path, capsys):
    p = _base(tmp_path)
    rc = main(['query', '--source-dir', str(p.parent), '--table', '_REFERENCE9',
               '--select', '_CODE,_QUANTITY', '--where', '_QUANTITY>4',
               '--order-by', '_QUANTITY DESC'])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True and out['count'] == 1
    assert out['rows'][0] == {'_CODE': '000000001', '_QUANTITY': 10.5}


def test_cli_query_error(tmp_path: Path, capsys):
    p = _base(tmp_path)
    rc = main(['query', '--source-dir', str(p.parent), '--table', '_NOPE'])
    assert rc == 1
    assert 'таблица не найдена' in capsys.readouterr().err


def test_cli_guid_diff_without_config(tmp_path: Path, capsys):
    """Синтетика без конфигурации: FormatError (DBNames) — rc=1 с сообщением."""
    p = _base(tmp_path)
    rc = main(['guid-diff', '--source-dir', str(p.parent),
               '--target-dir', str(p.parent)])
    assert rc == 1
    assert 'DBNames' in capsys.readouterr().err


BASE_83 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3/1Cv8.1CD')
REQUIRED_83 = pytest.mark.skipif(
    not BASE_83.is_file(), reason='реальная база 8.3 отсутствует')


@REQUIRED_83
@pytest.mark.integration
def test_cli_guid_diff_real(tmp_path: Path, capsys):
    """Позитивный сценарий: база сама с собой — full=True."""
    rc = main(['guid-diff', '--source-dir', str(BASE_83.parent),
               '--target-dir', str(BASE_83.parent)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True and out['full'] is True


def test_cli_config_versions(tmp_path: Path, capsys):
    p = _base(tmp_path)
    rc = main(['config-versions', '--source-dir', str(p.parent)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True and out['format'] == '8.3.8.0'
    assert 'config_files' in out and 'ibversion' in out


def test_cli_help_lists_new_commands(capsys):
    import pytest

    with pytest.raises(SystemExit):
        main(['--help'])
    out = capsys.readouterr().out
    assert 'query' in out and 'guid-diff' in out and 'config-versions' in out
