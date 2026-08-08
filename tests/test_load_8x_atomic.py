"""Фаза 16: атомарность, лимиты, чистка tmp в load_direct."""
from __future__ import annotations

import errno
from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import LoadError, load_direct
from onec_converter.write_8x import create_1cd

F_REFERENCE = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]
META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0}]},
]}


def _target(tmp_path: Path) -> Path:
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=F_REFERENCE,
                             rows=[encode_row(F_REFERENCE, {
                                 '_IDRREF': b'\x11' * 16, '_CODE': 'seed'})])])
    return tgt


def _obj(code: str) -> dict:
    return {'type': 'Справочник.Банки', 'key': [code],
            'attributes': {'Код': code}, 'references': {}}


def test_atomic_replace_final_created(tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: META)
    wd = tmp_path / 'wd'
    rep = load_direct(tgt, [_obj('00001')], workdir=wd,
                      verify_after=False)
    # финальный файл создан атомарно, work-файл удалён
    assert (wd / '1Cv8.1CD').is_file()
    assert not list(wd.glob('work*.1CD'))
    assert Path(rep['copy_path']) == wd / '1Cv8.1CD'


def test_enospc_raises_and_no_partial(tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: META)

    def boom(path, table_name, rows):
        raise OSError(errno.ENOSPC, 'No space left on device', path)

    monkeypatch.setattr('onec_converter.load_8x.append_records', boom)
    wd = tmp_path / 'wd'
    with pytest.raises(LoadError, match='недостаточно места'):
        load_direct(tgt, [_obj('00001')], workdir=wd, verify_after=False)
    # нет финального 1Cv8.1CD и нет полу-перезаписи; work удалён
    assert not (wd / '1Cv8.1CD').exists()
    assert not (wd / '1Cv8.1CD').is_file()
    assert not list(wd.glob('work*.1CD'))


def test_max_objects_limit(tmp_path: Path,
                           monkeypatch: pytest.MonkeyPatch):
    tgt = _target(tmp_path)
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: META)
    with pytest.raises(LoadError, match='max_objects'):
        load_direct(tgt, [_obj('00001'), _obj('00002')],
                    workdir=tmp_path / 'wd', max_objects=1)
