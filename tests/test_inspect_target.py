"""Unit-тесты inspect_target и правила 1→1."""
import pytest

from onec_converter.inspect_target import ProjectBinding, ProjectError, inspect_target_from_http


def test_binding_1to1_ok(tmp_path):
    b = ProjectBinding.create(tmp_path, 'srcA', 'tgtX')
    b.check('srcA', 'tgtX')  # не должно бросить


def test_binding_wrong_source_blocked(tmp_path):
    b = ProjectBinding.create(tmp_path, 'srcA', 'tgtX')
    with pytest.raises(ProjectError):
        b.check('srcB', 'tgtX')


def test_binding_load_roundtrip(tmp_path):
    ProjectBinding.create(tmp_path, 'srcA', 'tgtX')
    b = ProjectBinding.load(tmp_path)
    assert b.source_ib_id == 'srcA' and b.target_ib_id == 'tgtX'


def test_http_metadata_normalized():
    meta = {'Справочники': [{'Имя': 'Банки', 'Реквизиты': []}]}
    tm = inspect_target_from_http(meta)
    assert tm.find('Справочники.Банки') is not None
