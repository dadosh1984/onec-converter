"""Тесты CLI inspect: метаданные источника 7.7 и 8.x (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main
from onec_converter.fake_1cd import FixtureField, FixtureTable, write_fake_1cd
from tests.fixtures.gen_dat import make_dat


def _base77(tmp_path: Path) -> Path:
    base = tmp_path / 'base77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    return base


def test_inspect_77(tmp_path: Path, capsys):
    base = _base77(tmp_path)
    rc = main(['inspect', '--source-dir', str(base)])
    assert rc == 0
    meta = json.loads(capsys.readouterr().out)
    assert meta['version'] == '7.7'
    assert meta['references_tables'] == 1
    assert meta['unique_ids'] == {1: 2}


def test_inspect_77_cp1251(tmp_path: Path, capsys):
    base = tmp_path / 'base77m'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 1},
        references={1: [['1|', '0001', 'Иванов Иван Иванович']]},
        encoding='cp1251'))
    rc = main(['inspect', '--source-dir', str(base), '--source-encoding', 'cp1251'])
    assert rc == 0
    meta = json.loads(capsys.readouterr().out)
    assert meta['version'] == '7.7'
    assert meta['references_tables'] == 1


def test_inspect_8x(tmp_path: Path, capsys):
    t = FixtureTable('_REFERENCE3', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=150),
    ])
    cd = tmp_path / 'base8x'
    cd.mkdir()
    write_fake_1cd(cd / '1Cv8.1CD', [t])
    rc = main(['inspect', '--source-dir', str(cd)])
    assert rc == 0
    meta = json.loads(capsys.readouterr().out)
    assert meta['version'] == '8.x'
    assert '_REFERENCE3' in meta['tables']
