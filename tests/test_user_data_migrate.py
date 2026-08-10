"""bridge-migrate: пути, план, экспорт мостов, загрузка+обратный тест, CLI."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.bridge_export import export_bridge
from onec_converter.classify import build_plan
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd
from onec_converter.user_data_migrate import (check_paths, export_sections,
                                              load_and_verify)

F = [FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты', 'table': '_REFERENCE1',
     'attributes': [
         {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9,
          'precision': 0},
         {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string',
          'length': 40, 'precision': 0},
     ]},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная', 'table': '_DOCUMENT1',
     'attributes': [
         {'name': 'Номер', 'field': '_CODE', 'type': 'string', 'length': 9,
          'precision': 0},
     ]},
]}


def _base(tmp_path, name: str, rows: list[bytes] | None = None):
    p = tmp_path / name
    p.mkdir(exist_ok=True)
    (p / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp_path / f'{name}.1CD',
                       [FixtureTable('_REFERENCE1', fields=F, rows=rows or [])]))
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


def test_export_each_section_separate_file(tmp_path, monkeypatch):
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: dict(META))
    rows = [
        encode_row(F, {'_IDRREF': bytes.fromhex('02000000110000000000000000000000'),
                       '_CODE': '00001', '_DESCRIPTION': 'ООО Ромашка'}),
    ]
    src = _base(tmp_path, 'src', rows)
    out_dir = tmp_path / 'bridges'
    out_dir.mkdir()

    files = export_sections(src, build_plan(META), out_dir)
    assert len(files) == 1  # Документ мостом не выгружается — только Справочник
    names = {f.name for f in files}
    assert names == {'Справочник.Контрагенты.xlsx'}
    assert (out_dir / 'Справочник.Контрагенты.xlsx').is_file()


def test_load_and_verify_pilot_gate(monkeypatch):
    """Пилот: при несовпадении пилотной сверки полная загрузка не выполняется."""
    imports: list[int | None] = []

    def fake_import(bridge_path, target_dir, workdir=None, max_rows=None, **kw):
        imports.append(max_rows)
        return {'ok': True, 'created': 1, 'updated': 0, 'errors': [],
                'copy_path': str(Path('wd') / '1Cv8.1CD')}

    def fake_verify(*a, limit=None, **kw):
        if limit == 3:
            return {'ok': False, 'matched': 0, 'mismatched': 1, 'missing': 1,
                    'extra': 0, 'diffs': [{'key': ['1'], 'kind': 'different'}],
                    'in_rows': 3}
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'in_rows': 1}

    monkeypatch.setattr('onec_converter.user_data_migrate.import_bridge',
                        fake_import)
    monkeypatch.setattr('onec_converter.user_data_migrate.verify_roundtrip',
                        fake_verify)

    rep = load_and_verify(Path('b.xlsx'), Path('tgt'), 'Справочник.X',
                          Path('wd'), pilot_rows=3)
    assert rep['ok'] is False
    assert 'пилот' in rep['error']
    # только пилотная загрузка (max_rows=3) — полная (None) не делалась
    assert imports == [3]


def test_load_and_verify_pilot_then_full(monkeypatch):
    """Пилот ок -> полная загрузка -> полная сверка ок."""
    imports: list[int | None] = []
    limits: list[int | None] = []

    def fake_import(bridge_path, target_dir, workdir=None, max_rows=None, **kw):
        imports.append(max_rows)
        return {'ok': True, 'created': 1, 'updated': 0, 'errors': [],
                'copy_path': str(Path('wd') / '1Cv8.1CD')}

    def fake_verify(*a, limit=None, **kw):
        limits.append(limit)
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'in_rows': limit or 1}

    monkeypatch.setattr('onec_converter.user_data_migrate.import_bridge',
                        fake_import)
    monkeypatch.setattr('onec_converter.user_data_migrate.verify_roundtrip',
                        fake_verify)

    rep = load_and_verify(Path('b.xlsx'), Path('tgt'), 'Справочник.X',
                          Path('wd'), pilot_rows=3)
    assert rep['ok'] is True
    assert imports == [3, None]  # пилот -> полная загрузка
    assert limits == [3, None]   # пилотная сверка -> полная сверка
    assert rep['pilot']['ok'] is True


def test_load_and_verify_retries_until_ok(monkeypatch):
    attempts = {'n': 0}

    def fake_import(bridge_path, target_dir, workdir=None, max_rows=None, **kw):
        return {'ok': True, 'created': 1, 'updated': 0, 'errors': [],
                'copy_path': str(Path('wd') / '1Cv8.1CD')}

    def fake_verify(*a, limit=None, **kw):
        if limit is not None:
            return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                    'extra': 0, 'in_rows': 1}
        attempts['n'] += 1
        if attempts['n'] < 3:
            return {'ok': False, 'matched': 0, 'mismatched': 1, 'missing': 1,
                    'extra': 0, 'diffs': [{'row': 1, 'col': 'Код', 'in': '1',
                                           'out': '2'}],
                    'in_rows': 1}
        return {'ok': True, 'matched': 1, 'mismatched': 0, 'missing': 0,
                'extra': 0, 'in_rows': 1}

    monkeypatch.setattr('onec_converter.user_data_migrate.import_bridge',
                        fake_import)
    monkeypatch.setattr('onec_converter.user_data_migrate.verify_roundtrip',
                        fake_verify)

    rep = load_and_verify(Path('b.xlsx'), Path('tgt'), 'Справочник.X',
                          Path('wd'), max_tries=3)
    assert rep['ok'] is True
    assert attempts['n'] == 3


def test_parser_bridge_migrate():
    from onec_converter.cli import build_parser

    p = build_parser()
    args = p.parse_args([
        'bridge-migrate', '--source-dir', 'src', '--target-dir', 'tgt',
        '--workdir', 'wd', '--objects', 'Справочник.Контрагенты',
    ])
    assert args.source_dir == 'src'
    assert args.target_dir == 'tgt'
    assert args.workdir == 'wd'
    assert args.objects == 'Справочник.Контрагенты'


def test_cmd_bridge_migrate_invokes_run(monkeypatch, capsys):
    from onec_converter.cli import main as cli_main

    captured: dict = {}

    def fake_run(source_dir, target_dir, workdir=None, objects='',
                 meta=None, **kw):
        captured.update(source_dir=str(source_dir),
                        target_dir=str(target_dir),
                        workdir=str(workdir), objects=objects)
        return {'ok': True, 'plan': [], 'exported': 0, 'imported': 0}

    monkeypatch.setattr('onec_converter.user_data_migrate.run_migration',
                        fake_run)
    rc = cli_main(['bridge-migrate', '--source-dir', 'src',
                   '--target-dir', 'tgt', '--workdir', 'wd'])
    assert rc == 0
    assert captured['source_dir'] == 'src'
    assert captured['target_dir'] == 'tgt'
    assert captured['objects'] == ''


def test_commands_map_mentions_bridge_migrate():
    cm = Path(__file__).resolve().parent.parent / 'docs' / 'commands-map.md'
    if not cm.is_file():
        return
    assert 'bridge-migrate' in cm.read_text(encoding='utf-8')


def test_e2e_source_to_target_copy(tmp_path, monkeypatch):
    """Сквозной цикл: fake-источник -> план -> экспорт моста -> загрузка
    в копию приёмника -> обратный тест ок."""
    from onec_converter.user_data_migrate import run_migration

    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: dict(META))
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: dict(META))
    rows = [
        encode_row(F, {'_IDRREF': bytes.fromhex('02000000110000000000000000000000'),
                       '_CODE': '00001', '_DESCRIPTION': 'ООО Ромашка'}),
        encode_row(F, {'_IDRREF': bytes.fromhex('02000000220000000000000000000000'),
                       '_CODE': '00002', '_DESCRIPTION': 'ООО Поле'}),
    ]
    src = _base(tmp_path, 'src', rows)
    tgt = _base(tmp_path, 'tgt', [encode_row(F, {})])  # пустой приёмник (1 служебная строка)
    wd = tmp_path / 'workdir'

    rep = run_migration(src, tgt, workdir=wd, objects='Справочник.Контрагенты',
                        meta=dict(META))
    assert rep['ok'] is True
    assert rep['exported'] == 1
    assert len(rep['plan']) == 1
    sec = rep['sections']['Справочник.Контрагенты']
    assert sec['ok'] is True
    assert (wd / 'target_copy' / '1Cv8.1CD').is_file()
