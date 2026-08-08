"""Тесты CLI status: состояние пайплайна (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main


def test_status_empty_project(tmp_path: Path, capsys):
    """Пустой project-dir: коннекторы не настроены, кеш пуст, last_step None."""
    rc = main(['status', '--project-dir', str(tmp_path)])
    assert rc == 0
    st = json.loads(capsys.readouterr().out)
    assert st['ok'] is True
    assert st['connectors']['file']['configured'] is False
    assert st['connectors']['http']['configured'] is False
    assert st['cache']['entries'] == 0
    assert st['last_step'] is None


def test_status_after_init(tmp_path: Path, capsys):
    """После init: файловый коннектор настроен, last_step='init'."""
    base = tmp_path / 'base77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(b'')
    # init в PipelineState напрямую (CLI status не имеет init-команды)
    from onec_converter.mcp_server import PipelineState
    st = PipelineState(tmp_path / 'proj')
    r = st.step_init(str(tmp_path / 'proj'), 'srcA', 'tgtX', str(base))
    assert r['ok']
    rc = main(['status', '--project-dir', str(tmp_path / 'proj')])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['connectors']['file']['configured'] is True
    assert out['last_step'] == 'init'
    assert out['binding'] == {'source': 'srcA', 'target': 'tgtX'}
