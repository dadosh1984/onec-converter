"""Unit-тесты шагов пайплайна MCP-сервера."""
import json
from pathlib import Path

import pytest

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
    assert ext['objects'] == 2    # повторный inspect — из кеша
    ins2 = st.step_inspect_source()
    assert ins2['cached'] is True
    rules = {'version': 1, 'objects': [
        {'source': 'Справочник.1', 'target': 'Справочник.1', 'key': ['_code'],
         'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}
    m = st.step_map({}, {}, rules)
    assert m['ok']
    pv = st.step_prevalidate()
    assert pv['ok'] and pv['counts']['Справочник.1'] == 2


def test_step_extract_objects_filter(tmp_path: Path):
    base = _make_state(tmp_path)
    st = PipelineState(tmp_path / 'proj')
    st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    # группа Справочник.* — всё
    ext_all = st.step_extract(str(tmp_path / 'out1.json'), objects='Справочник.*')
    assert ext_all['objects'] == 2
    # точный объект — только его записи
    ext_one = st.step_extract(str(tmp_path / 'out2.json'), objects='Справочник.1')
    assert ext_one['objects'] == 2
    # несуществующий раздел — пусто
    ext_none = st.step_extract(str(tmp_path / 'out3.json'), objects='Документ.*')
    assert ext_none['objects'] == 0


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


def test_table_sizes_tool(tmp_path: Path):
    """A2: размеры таблиц 1CD — строки и байты на таблицу."""
    from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
    from onec_converter.mcp_server import table_sizes

    t = FixtureTable('_REFERENCE1', fields=[
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_DESCRIPTION', 'NVC', length=10),
    ], rows=[
        encode_row([FixtureField('_IDRREF', 'B', length=16),
                    FixtureField('_DESCRIPTION', 'NVC', length=10)],
                   {'_IDRREF': b'\x01' * 16, '_DESCRIPTION': 'А'}),
    ])
    (tmp_path / '1Cv8.1CD').write_bytes(build_fake_1cd([t]))
    res = table_sizes(str(tmp_path))
    import json
    d = json.loads(res)
    assert d['ok'] and d['count'] == 1
    assert d['tables']['_REFERENCE1']['rows'] == 1
    assert d['tables']['_REFERENCE1']['bytes'] > 0
    # фильтр
    d2 = json.loads(table_sizes(str(tmp_path), tables='REFERENCE1'))
    assert d2['count'] == 1
    d3 = json.loads(table_sizes(str(tmp_path), tables='NOPE'))
    assert d3['count'] == 0
    # format='xlsx' — файл-отчёт
    out = tmp_path / 'sizes.xlsx'
    rx = json.loads(table_sizes(str(tmp_path), format='xlsx', out_file=str(out)))
    assert rx['ok'] and out.is_file() and out.stat().st_size > 0


def test_timings_histogram():
    """A3: журнал метрик времени — histogram по операциям."""
    from onec_converter.timings import Timings

    t = Timings()
    t.record('read_metadata:Справочник', 1.5)
    t.record('read_metadata:Справочник', 3.5)
    t.record('read_metadata:Документ', 2.0)
    s = t.snapshot()
    assert s['read_metadata:Справочник']['count'] == 2
    assert s['read_metadata:Справочник']['total_ms'] == 5.0
    assert s['read_metadata:Справочник']['avg_ms'] == 2.5
    assert s['read_metadata:Справочник']['max_ms'] == 3.5
    assert s['read_metadata:Документ']['count'] == 1


def test_cp1251_middleware(tmp_path: Path):
    """A4: CP1251→UTF-8 middleware — строки 7.7 в CP1251 доходят до JSON без искажений."""
    from onec_converter.base_reader import Base77
    from onec_converter.intermediate import save_json_batch
    from tests.fixtures.gen_dat import make_dat

    base = tmp_path / 'base1251'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар «Ковёр»'], ['2|', '0002', 'Наименование: №5']]},
        encoding='cp1251'))
    src = Base77(base, encoding='cp1251')
    refs = src.data.references()[1]
    assert refs[0][2] == 'Товар «Ковёр»'
    assert refs[1][2] == 'Наименование: №5'
    # промежуточный JSON — UTF-8 (байты CP1251 не протекают)
    out = tmp_path / 'out.json'
    save_json_batch([{'ib': 'src', 'type': 'Справочник', 'name': 'Товары',
                      'records': [{'id': r[0], 'code': r[1], 'name': r[2]} for r in refs]}], str(out))
    text = out.read_bytes().decode('utf-8')
    assert 'Товар «Ковёр»' in text
    # cp866 по умолчанию ломает cp1251-строки (контроль middleware)
    src2 = Base77(base)
    refs2 = src2.data.references()[1]
    assert refs2[0][2] != 'Товар «Ковёр»'


def test_search_schema_tool(tmp_path: Path):
    """C1: двунаправленный поиск метаданные↔таблицы."""
    from onec_converter.fake_1cd import build_fake_1cd
    from onec_converter.mcp_server import search_schema
    from tests.test_source_8x_units import _config_tables

    (tmp_path / '1Cv8.1CD').write_bytes(build_fake_1cd(_config_tables()))
    res = json.loads(search_schema(str(tmp_path), 'Банки'))
    assert res['ok']
    assert any(o['name'] == 'Банки' for o in res['objects'])
    assert res['objects'][0]['table'] == '_REFERENCE3'
    res2 = json.loads(search_schema(str(tmp_path), 'REFERENCE3'))
    assert any(o['table'] == '_REFERENCE3' for o in res2['objects'])


def test_compare_structures_tool(tmp_path: Path):
    """C2: diff-отчёт структур — объекты/типы в двух базах."""
    from onec_converter.fake_1cd import FixtureField, build_fake_1cd
    from onec_converter.mcp_server import compare_structures
    from tests.test_source_8x_units import _config_tables

    (tmp_path / 'src').mkdir()
    (tmp_path / 'tgt').mkdir()
    (tmp_path / 'src' / '1Cv8.1CD').write_bytes(build_fake_1cd(_config_tables()))
    # приёмник: другой объект (только в приёмнике) + поле другого типа
    tables = _config_tables()
    ref = tables[2]
    ref.fields.append(FixtureField('_EXTRA', 'N', length=6, precision=0))
    (tmp_path / 'tgt' / '1Cv8.1CD').write_bytes(build_fake_1cd(tables))
    res = json.loads(compare_structures(str(tmp_path / 'src'),
                                        str(tmp_path / 'tgt')))
    assert res['ok']
    assert res['counts']['only_target'] == 0  # объекты одинаковы (имя/kind)
    assert res['counts']['mismatch'] == 0
    # format='xlsx' — файл-отчёт
    out = tmp_path / 'struct.xlsx'
    rx = json.loads(compare_structures(str(tmp_path / 'src'),
                                       str(tmp_path / 'tgt'),
                                       format='xlsx', out_file=str(out)))
    assert rx['ok'] and out.is_file() and out.stat().st_size > 0
    # xlsx без out_file — ошибка
    re_ = json.loads(compare_structures(str(tmp_path / 'src'),
                                        str(tmp_path / 'tgt'),
                                        format='xlsx'))
    assert not re_['ok']


def test_query_table_tool(tmp_path: Path):
    """C3: консоль запросов — фильтрация записей по условиям (query_sql)."""
    from onec_converter.fake_1cd import build_fake_1cd
    from onec_converter.mcp_server import query_sql
    from tests.test_source_8x_units import _config_tables, ref_rows

    tables = _config_tables()
    tables[2].rows = ref_rows()
    (tmp_path / '1Cv8.1CD').write_bytes(build_fake_1cd(tables))
    res = json.loads(query_sql(str(tmp_path), '_REFERENCE3',
                               where='_DESCRIPTION=Тест один'))
    assert res['ok']
    assert res['count'] >= 1
    assert all(r['_DESCRIPTION'] == 'Тест один' for r in res['rows'])


def test_dump_metadata_tool(tmp_path: Path):
    """D1: dump_metadata — YAML/JSON дамп метаданных в файл (git-дружественно)."""
    from onec_converter.fake_1cd import build_fake_1cd
    from onec_converter.mcp_server import dump_metadata
    from tests.test_source_8x_units import _config_tables

    (tmp_path / '1Cv8.1CD').write_bytes(build_fake_1cd(_config_tables()))
    out = tmp_path / 'meta.json'
    res = json.loads(dump_metadata(str(tmp_path), str(out), fmt='json'))
    assert res['ok'] and res['objects'] == 1
    text = out.read_text(encoding='utf-8')
    assert '"Банки"' in text
    yaml_out = tmp_path / 'meta.yaml'
    res_y = json.loads(dump_metadata(str(tmp_path), str(yaml_out), fmt='yaml'))
    assert res_y['ok']
    assert 'Банки' in yaml_out.read_text(encoding='utf-8')


def test_playbook_sequence():
    """Плейбук: 16 шагов, next-поля согласованы, вшиваются в JSON-ответы."""
    import json as _json
    from pathlib import Path as _Path

    from onec_converter.mcp_server import PLAYBOOK, PLAYBOOK_NEXT, playbook

    steps = _json.loads(playbook())
    assert steps['ok'] and len(steps['steps']) == 16
    cmds = [p['command'].split('(')[0] for p in PLAYBOOK]
    assert cmds[0] == 'tools'
    assert 'step_init' in cmds and 'step_load' in cmds and 'verify' in cmds
    # next-поля согласованы
    for tool, nxt in PLAYBOOK_NEXT.items():
        assert nxt and tool, tool
    # next вшивается в JSON-ответы (на синтетике/или skip при отсутствии базы)
    from onec_converter.mcp_server import query_sql
    base = _Path('1C_8.1/1Cv8.1CD')
    if not base.is_file():
        pytest.skip('реальная база 8.1 отсутствует — проверка next пропущена')
    res = _json.loads(query_sql('1C_8.1', '_REFERENCE3', where='_CODE=00001', limit=1))
    assert 'next' in res and res['ok']


def test_terminal_visibility(capsys):
    """Терминальная видимость: события пишутся в stderr (не в stdout)."""
    from onec_converter.terminal import now_ms, tool_error, tool_finished, tool_started

    tool_started('table_sizes', "'1C_8.1', 'Reference'")
    tool_finished('table_sizes', True, 12.5, 'ok=True, count=75')
    tool_error('query_table', 3.0, 'таблица не найдена: _XXX')
    captured = capsys.readouterr()
    assert captured.out == ''            # stdout чист (JSON-RPC)
    err = captured.err
    assert '[onec-converter' in err
    assert '▶ table_sizes' in err and '✔ table_sizes' in err
    assert '✘ query_table' in err
    assert '12 ms' in err
    assert now_ms() > 0
