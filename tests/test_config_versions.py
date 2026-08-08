"""Unit-тесты версий конфигурации (Фаза 11, E3): config_versions.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.config_versions import _diff, config_versions
from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
from onec_converter.source_8x_file import Database1CD


def _config_table(name: str, files: list[tuple[str, int]]) -> FixtureTable:
    fields = [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('FILENAME', 'NVC', length=64),
        FixtureField('CREATION', 'DT'),
        FixtureField('MODIFIED', 'DT'),
        FixtureField('ATTRIBUTES', 'N', length=5),
        FixtureField('DATASIZE', 'N', length=20),
        FixtureField('BINARYDATA', 'I'),
        FixtureField('PARTNO', 'N', length=10),
    ]
    rows = [encode_row(fields, {'FILENAME': nm, 'DATASIZE': sz})
            for nm, sz in files]
    return FixtureTable(name, fields=fields, rows=rows)


def _ibversion_table() -> FixtureTable:
    fields = [FixtureField('IBVERSION', 'N', length=10),
              FixtureField('PLATFORMVERSIONREQ', 'N', length=10)]
    return FixtureTable('IBVERSION', fields=fields,
                        rows=[encode_row(fields, {'IBVERSION': 0,
                                                  'PLATFORMVERSIONREQ': 0}),
                              encode_row(fields, {'IBVERSION': 7,
                                                  'PLATFORMVERSIONREQ': 80313})])


@pytest.fixture
def base(tmp_path: Path) -> Path:
    tables = [
        _config_table('CONFIG', [('cfg-a', 100), ('cfg-b', 200)]),
        _config_table('CONFIGSAVE', [('cfg-a', 150)]),
        _config_table('PARAMS', [('locale.inf', 42)]),
        _ibversion_table(),
    ]
    p = tmp_path / 'base.1CD'
    p.write_bytes(build_fake_1cd(tables))
    return p


def test_config_versions_shape(base: Path):
    rep = config_versions(base)
    assert rep['ok'] is True
    assert rep['format'] == '8.3.8.0'
    assert rep['config_files']['CONFIG']['count'] == 2
    assert rep['config_files']['CONFIGSAVE']['count'] == 1
    assert rep['config_files']['PARAMS']['count'] == 1
    assert rep['ibversion'] == [
        {'IBVERSION': 0, 'PLATFORMVERSIONREQ': 0},
        {'IBVERSION': 7, 'PLATFORMVERSIONREQ': 80313},
    ]


def test_config_vs_configsave_diff(base: Path):
    rep = config_versions(base)
    d = rep['config_vs_configsave']
    assert d['added'] == []
    assert d['removed'] == ['cfg-b']          # есть только в CONFIG
    assert d['changed'] == ['cfg-a']          # размеры различаются


def test_diff_empty():
    assert _diff([], []) == {'added': [], 'removed': [], 'changed': []}
    src = [('a', None, None, 1)]
    tgt = [('a', None, None, 1), ('b', None, None, 2)]
    d = _diff(src, tgt)
    assert d['added'] == ['b']
    assert d['removed'] == []
    assert d['changed'] == []


def test_config_versions_readable_by_parser(base: Path):
    """Созданная база читается парсером — целостность фикстуры."""
    with Database1CD(base) as db:
        assert 'CONFIG' in db.tables
        assert 'IBVERSION' in db.tables
