"""Проверка путей оригиналов и копия приёмника в workdir."""
from __future__ import annotations

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, write_fake_1cd
from onec_converter.user_data_migrate import check_paths

F = [FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]


def _base(tmp_path, name: str):
    p = tmp_path / name
    p.mkdir(exist_ok=True)
    (p / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / f'{name}.1CD',
                       [FixtureTable('_REFERENCE1', fields=F, rows=[])]))
    return p


def test_check_paths_ok(tmp_path):
    src = _base(tmp_path, 'src')
    tgt = _base(tmp_path, 'tgt')
    rep = check_paths(src, tgt)
    assert rep['ok'] is True


def test_check_paths_missing_source(tmp_path):
    tgt = _base(tmp_path, 'tgt')
    rep = check_paths(tmp_path / 'nope', tgt)
    assert rep['ok'] is False
    assert 'источник' in rep['error']


def test_check_paths_same_dir(tmp_path):
    d = _base(tmp_path, 'both')
    rep = check_paths(d, d)
    assert rep['ok'] is False
    assert 'одна и та же' in rep['error']


"""Экспорт разделов плана в отдельные xlsx-мосты."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.bridge_export import export_bridge
from onec_converter.classify import build_plan
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd

F = [FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE1',
     'attributes': [
         {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9, 'precision': 0},
         {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string', 'length': 40, 'precision': 0},
     ]},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная', 'table': '_DOCUMENT1',
     'attributes': [
         {'name': 'Номер', 'field': '_CODE', 'type': 'string', 'length': 9, 'precision': 0},
     ]},
]}


def test_export_each_section_separate_file(tmp_path, monkeypatch):
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: dict(META))
    rows = [
        encode_row(F, {'_IDRREF': bytes.fromhex('02000000110000000000000000000000'),
                       '_CODE': '00001', '_DESCRIPTION': 'ООО Ромашка'}),
    ]
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / 'base.1CD',
                       [FixtureTable('_REFERENCE1', fields=F, rows=rows),
                        FixtureTable('_DOCUMENT1', fields=F, rows=[])]))
    out_dir = tmp_path / 'bridges'
    out_dir.mkdir()

    from onec_converter.user_data_migrate import export_sections
    files = export_sections(src, build_plan(META), out_dir)
    assert len(files) == 2
    names = {f.name for f in files}
    assert names == {'Справочник.Контрагенты.xlsx', 'Документ.ПриходнаяНакладная.xlsx'}
    assert (out_dir / 'Справочник.Контрагенты.xlsx').is_file()


"""Цикл загрузки и обратного теста по одному файлу."""
from __future__ import annotations

from onec_converter.user_data_migrate import load_and_verify


def test_load_and_verify_ok(monkeypatch):
    calls: list[str] = []
    reports: list[dict] = []

    def fake_import(bridge_path, target_dir, workdir=None, **kw):
        calls.append('import')
        return {'ok': True, 'created': 1, 'updated': 0, 'errors': []}

    def fake_verify(*a, **kw):
        reports.append(dict(kw))
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'in_rows': 1}

    monkeypatch.setattr('onec_converter.user_data_migrate.import_bridge', fake_import)
    monkeypatch.setattr('onec_converter.user_data_migrate.verify_roundtrip', fake_verify)

    rep = load_and_verify(Path('b.xlsx'), Path('tgt'), Path('wd'))
    assert rep['ok'] is True
    assert calls == ['import', 'import']  # 2-й прогон: исходная копия + после записи


def test_load_and_verify_retries_until_ok(monkeypatch):
    attempts = {'n': 0}

    def fake_import(bridge_path, target_dir, workdir=None, **kw):
        return {'ok': True, 'created': 1, 'updated': 0, 'errors': []}

    def fake_verify(*a, **kw):
        attempts['n'] += 1
        if attempts['n'] < 3:
            return {'ok': False, 'matched': 0, 'mismatched': 1, 'missing': 1,
                    'extra': 0, 'diffs': [{'row': 1, 'col': 'Код', 'in': '1', 'out': '2'}],
                    'in_rows': 1}
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'in_rows': 1}

    monkeypatch.setattr('onec_converter.user_data_migrate.import_bridge', fake_import)
    monkeypatch.setattr('onec_converter.user_data_migrate.verify_roundtrip', fake_verify)

    rep = load_and_verify(Path('b.xlsx'), Path('tgt'), Path('wd'), max_tries=3)
    assert rep['ok'] is True
    assert attempts['n'] == 3


"""CLI: команда bridge-migrate."""
from __future__ import annotations

from onec_converter.cli import build_parser
from onec_converter.cli import main as cli_main


def test_parser_bridge_migrate():
    p = build_parser()
    args = p.parse_args([
        'bridge-migrate', '--source-dir', 'src', '--target-dir', 'tgt',
        '--workdir', 'wd', '--objects', 'Справочник.Контрагенты',
    ])
    assert args.source_dir == 'src'
    assert args.target_dir == 'tgt'
    assert args.workdir == 'wd'
    assert args.objects == 'Справочник.Контрагенты'


def test_cmd_bridge_migrate_invokes_run(monkeypatch):
    captured: dict = {}

    def fake_run(source_dir, target_dir, workdir=None, objects='',
                 meta=None, **kw):
        captured.update(source_dir=str(source_dir), target_dir=str(target_dir),
                        workdir=str(workdir), objects=objects)
        return {'ok': True, 'plan': [], 'exported': 0, 'imported': 0}

    monkeypatch.setattr('onec_converter.user_data_migrate.run_migration', fake_run)
    rc = cli_main(['bridge-migrate', '--source-dir', 'src',
                   '--target-dir', 'tgt', '--workdir', 'wd'])
    assert rc == 0
    assert captured['source_dir'] == 'src'
    assert captured['target_dir'] == 'tgt'


