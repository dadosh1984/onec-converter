"""Интеграционные тесты engine.run_pipeline()."""

from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.engine import PipelineResult, run_pipeline
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.write_8x import create_1cd

_META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [
         {'name': 'Код', 'field': '_CODE', 'type': 'NC',
          'length': 9, 'precision': 0},
         {'name': 'Наименование', 'field': '_DESCRIPTION',
          'type': 'NVC', 'length': 40, 'precision': 0},
     ]},
]}

_FIELDS = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]


def test_engine_empty_input(tmp_path: Path, monkeypatch) -> None:
    """Пустой объект + 1CD seed-строкой = ok."""
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: _META)
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=_FIELDS,
                             rows=[encode_row(_FIELDS, {
                                 '_IDRREF': b'\x11' * 16,
                                 '_CODE': '00000',
                                 '_DESCRIPTION': 'seed'})])])

    result = run_pipeline([], tgt)
    assert result.ok is True
    assert result.total == 0


def test_engine_single_object(tmp_path: Path, monkeypatch) -> None:
    """Один объект записывается."""
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: _META)
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=_FIELDS,
                             rows=[encode_row(_FIELDS, {
                                 '_IDRREF': b'\x11' * 16,
                                 '_CODE': '00000',
                                 '_DESCRIPTION': 'seed'})])])

    obj = {
        'type': 'Справочник.Банки',
        'key': ['001'],
        'attributes': {'Код': '001', 'Наименование': 'Тестовый банк'},
        'references': {},
    }
    wd = tmp_path / 'wd'
    wd.mkdir()
    result = run_pipeline([obj], tgt, workdir=wd)
    assert result.ok is True, f'errors: {result.errors}'
    assert result.total == 1


def test_engine_missing_target(tmp_path: Path) -> None:
    """Нет 1Cv8.1CD — ошибка, не паника."""
    tgt = tmp_path / 'empty'
    tgt.mkdir()
    result = run_pipeline([{'type': 'test', 'key': []}], tgt)
    assert result.ok is False
    assert len(result.errors) > 0
