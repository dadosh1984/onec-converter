"""Фаза 53 (0.36.0): Продукт и востребованность — U11/U12/U13/U15/U16,
U51-U55, U62. Новые CLI-команды: stats, mcp, export-xlsx, map --init,
doctor --fix; документы format-8x / бухгалтерия-77-в-83 / облачные-среды;
README матрица команд."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _fake_base(tmp_path: Path) -> Path:
    from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd

    b = tmp_path / 'base'
    b.mkdir()
    (b / '1Cv8.1CD').write_bytes(build_fake_1cd([
        FixtureTable(name='_REFERENCE1',
                     fields=[FixtureField('_IDRREF', 'B', length=16),
                             FixtureField('_CODE', 'NC', length=9),
                             FixtureField('_DESCRIPTION', 'NVC', length=40)],
                     rows=[b'\x01' * 16 + b'00001' + b'Bank'.ljust(40, b'\x00')])]))
    return b


# ---- U16: stats ----

def test_stats_command(tmp_path: Path):
    from onec_converter import cli

    b = _fake_base(tmp_path)
    rc = cli.main(['stats', '--source-dir', str(b)])
    assert rc == 0


def test_stats_no_base_fails(tmp_path: Path):
    from onec_converter import cli

    assert cli.main(['stats', '--source-dir', str(tmp_path)]) == 1


# ---- U15: mcp ----

def test_mcp_command_lists_tools():
    from onec_converter import cli

    rc = cli.main(['mcp'])
    assert rc == 0


# ---- U11: export-xlsx ----

def test_export_xlsx_command(tmp_path: Path):
    from onec_converter import cli

    b = _fake_base(tmp_path)
    out = tmp_path / 't.xlsx'
    rc = cli.main(['export-xlsx', '--source-dir', str(b),
                   '--table', '_REFERENCE1', '--limit', '10',
                   '--out', str(out)])
    assert rc == 0 and out.is_file()


# ---- U12: map --init ----

def test_map_init_requires_meta(tmp_path: Path):
    from onec_converter import cli

    assert cli.main(['map', '--init', '--meta-source', 'x', '--out', 'y']) == 1


def test_map_init_generates_rules(tmp_path: Path):
    from onec_converter import cli

    meta = tmp_path / 'meta.json'
    meta.write_text(json.dumps({'objects': [
        {'kind': 'Справочник', 'name': 'Банки',
         'attributes': [{'name': 'Наименование'}, {'name': 'ИНН'}]},
        {'kind': 'Документ', 'name': 'Платежка'},
    ]}), encoding='utf-8')
    out = tmp_path / 'rules.json'
    assert cli.main(['map', '--init', '--meta-source', str(meta),
                     '--out', str(out)]) == 0
    rules = json.loads(out.read_text(encoding='utf-8'))
    assert rules['version'] == 1
    assert rules['objects'][0]['source'] == 'Справочник.Банки'
    assert rules['objects'][0]['target'] == ''
    assert 'ИНН' in rules['objects'][0]['attributes']


# ---- U13: doctor --fix ----

def test_doctor_fix_runs(tmp_path: Path, monkeypatch):
    from onec_converter import cli

    monkeypatch.chdir(tmp_path)
    rc = cli.main(['doctor', '--fix'])
    assert rc in (0, 1)  # не падает; --fix может не установить зависимости
    assert (tmp_path / '.onec_cache').is_dir()


# ---- U62: schema_version уже в TOON ----

def test_toon_schema_version_present():
    from onec_converter.mapping import SCHEMA_VERSION

    assert SCHEMA_VERSION == 1
    # выдача (ai-map, map, transform) несёт version
    from onec_converter.mapping import RULES_DEFAULT

    assert RULES_DEFAULT.get('version') == SCHEMA_VERSION


# ---- Документы (U52/U53/U54/US1) ----

@pytest.mark.parametrize('rel', [
    'docs/format-8x.md',
    'docs/recipes/бухгалтерия-77-в-83.md',
    'docs/recipes/облачные-среды.md',
])
def test_product_docs_exist(rel: str):
    assert (ROOT / rel).is_file(), f'нет документа {rel}'


def test_readme_has_command_matrix():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'Матрица команд' in readme
    assert 'export-xlsx' in readme and 'stats' in readme
