"""Unit-тесты сравнения ИБ по GUID (Фаза 11, E2): guid_diff.py."""
from __future__ import annotations

import pytest

from onec_converter.guid_diff import guid_diff


def _run(monkeypatch: pytest.MonkeyPatch, src_objs: dict, tgt_objs: dict,
         src_tabs: dict, tgt_tabs: dict) -> dict:
    def _md(path: object) -> dict:
        objs = src_objs if 'src' in str(path) else tgt_objs
        return {'objects': [
            {'guid': g, 'kind': o['kind'], 'name': o['name'],
             'table': o.get('table', '')}
            for g, o in objs.items()]}

    monkeypatch.setattr('onec_converter.guid_diff.read_metadata', _md)
    monkeypatch.setattr('onec_converter.guid_diff._tables',
                        lambda path: tgt_tabs if 'tgt' in str(path)
                        else src_tabs)
    return guid_diff('/src', '/tgt')


def test_identical_bases_full(monkeypatch: pytest.MonkeyPatch):
    objs = {'g1': {'kind': 'Справочник', 'name': 'Номенклатура'},
            'g2': {'kind': 'Документ', 'name': 'Продажа'}}
    tabs = {'g1': ('Reference', 42), 'g2': ('Document', 7)}
    rep = _run(monkeypatch, objs, dict(objs), tabs, dict(tabs))
    assert rep['full'] is True
    assert rep['objects']['only_source'] == []
    assert rep['objects']['only_target'] == []
    assert rep['objects']['name_mismatch'] == []
    assert rep['objects']['common'] == 2
    assert rep['tables']['common'] == 2


def test_only_source_and_target(monkeypatch: pytest.MonkeyPatch):
    src = {'g1': {'kind': 'Справочник', 'name': 'Номенклатура'}}
    tgt = {'g2': {'kind': 'Документ', 'name': 'Продажа'}}
    rep = _run(monkeypatch, src, tgt, {}, {})
    assert rep['full'] is False
    assert [o['guid'] for o in rep['objects']['only_source']] == ['g1']
    assert [o['guid'] for o in rep['objects']['only_target']] == ['g2']


def test_name_mismatch_same_guid(monkeypatch: pytest.MonkeyPatch):
    src = {'g1': {'kind': 'Справочник', 'name': 'Номенклатура'}}
    tgt = {'g1': {'kind': 'Справочник', 'name': 'Номенклатура2'}}
    rep = _run(monkeypatch, src, tgt, {}, {})
    assert rep['full'] is False
    assert len(rep['objects']['name_mismatch']) == 1
    assert rep['objects']['name_mismatch'][0]['guid'] == 'g1'


def test_tables_only_in_source(monkeypatch: pytest.MonkeyPatch):
    tabs_src = {'g1': ('Reference', 42), 'g2': ('ReferenceChngR', 30415)}
    tabs_tgt = {'g1': ('Reference', 42)}
    rep = _run(monkeypatch, {}, {}, tabs_src, tabs_tgt)
    assert rep['full'] is False
    assert [t['guid'] for t in rep['tables']['only_source']] == ['g2']
    assert rep['tables']['common'] == 1
