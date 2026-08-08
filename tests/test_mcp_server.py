"""Unit-тесты шагов пайплайна MCP-сервера."""
from pathlib import Path

from onec_converter.mcp_server import PipelineState
from tests.fixtures.gen_dat import make_dat


def _make_state(tmp_path: Path):
    base = tmp_path / 'base'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    return base


def test_full_pipeline(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    r = st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    assert r['ok']
    ins = st.step_inspect_source()
    assert ins['ok'] and ins['metadata']['references_tables'] == 1
    ext = st.step_extract(str(tmp_path / 'out.json'))
    assert ext['objects'] == 2
    # повторный inspect — из кеша
    ins2 = st.step_inspect_source()
    assert ins2['cached'] is True
    rules = {'version': 1, 'objects': [
        {'source': 'Справочник.1', 'target': 'Справочник.1', 'key': ['_code'],
         'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}
    m = st.step_map({}, {}, rules)
    assert m['ok']
    pv = st.step_prevalidate()
    assert pv['ok'] and pv['counts']['Справочник.1'] == 2


def test_binding_blocks_wrong_source(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    import pytest

    from onec_converter.inspect_target import ProjectBinding, ProjectError
    with pytest.raises(ProjectError):
        ProjectBinding.load(tmp_path / 'proj').check('srcB', 'tgtX')


def test_status_connectors_cache_last_step(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    # до init — коннектор не настроен, последнего шага нет
    s0 = st.step_status()
    assert s0['ok']
    assert s0['connectors']['file']['configured'] is False
    assert s0['last_step'] is None
    assert s0['binding'] is None

    st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    s1 = st.step_status()
    assert s1['connectors']['file']['configured'] is True
    assert s1['last_step'] == 'init'
    assert s1['binding'] == {'source': 'srcA', 'target': 'tgtX'}
    # http/sql ещё не настроены
    assert s1['connectors']['http']['configured'] is False
    assert s1['connectors']['sql']['configured'] is False

    st.step_inspect_source()  # первичный разбор — кеш заполняется
    st.step_inspect_source()  # повторный — попадание в кеш
    s2 = st.step_status()
    assert s2['last_step'] == 'inspect_source'
    assert s2['cache']['hits'] == 1
    assert s2['cache']['entries'] >= 1
    assert s2['cache']['bytes'] > 0
