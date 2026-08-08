"""Фаза 26: техжурнал 1С как источник событий."""
from __future__ import annotations

import json

import pytest

from onec_converter.source_techlog import TechLog, TechLogError, parse_techlog_line

LINE_OK = ('20230620123000.123-0000000005-2|rphost,1,Srvr="s1":Process="p1",'
           'SDBL,2|dbpid=456|conn=78|p:processName=test_ibase|')


def test_parse_line():
    rec = parse_techlog_line(LINE_OK)
    assert rec is not None
    assert rec['ts'] == '2023-06-20T12:30:00.123000+00:00'
    assert rec['duration_ms'] == 5 and rec['level'] == 2
    assert rec['process'] == 'rphost' and rec['direction'] == 1
    assert rec['event'] == 'SDBL'
    assert rec['fields']['dbpid'] == '456'
    assert rec['fields']['p:processName'] == 'test_ibase'


def test_parse_line_garbage():
    assert parse_techlog_line('мусорная строка') is None
    assert parse_techlog_line('') is None
    assert parse_techlog_line('20230620123000.xxx-1-2|rphost,1,c,e,2|') is None


def test_techlog_errors():
    with pytest.raises(TechLogError):
        TechLog('E:/несуществующий/каталог/никогда')


def _write_log(tmp_path, name: str, lines: list[str]):
    (tmp_path / name).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def test_read_events_filters(tmp_path):
    _write_log(tmp_path, 'rphost_20230620120000.log', [
        LINE_OK,
        LINE_OK.replace('rphost,1,', 'rphost,0,').replace('SDBL,2|', 'EXCP,3|')
        .replace('dbpid=456', 'dbpid=777'),
    ])
    _write_log(tmp_path, 'rmngr_20230620120000.log', [
        LINE_OK.replace('rphost,1,', 'rmngr,1,'),
    ])
    tl = TechLog(tmp_path)
    assert len(tl.files()) == 2

    all_ev = tl.read_events()
    assert all_ev['ok'] and all_ev['count'] == 3

    sdb = tl.read_events(event='SDBL')
    assert sdb['count'] == 2
    assert all(e['event'] == 'SDBL' for e in sdb['events'])

    rph = tl.read_events(process='rphost')
    assert rph['count'] == 2

    ex = tl.read_events(event='EXCP')
    assert ex['count'] == 1
    # уровень в голове строки (2) и хвосте события (3) — оба сохраняются
    assert ex['events'][0]['level'] == 2 and ex['events'][0]['level2'] == 3
    assert ex['events'][0]['fields']['dbpid'] == '777'

    # фильтр по уровню головы: level>=2 — все, level>=3 — ни одного
    assert tl.read_events(level_min=2)['count'] == 3
    assert tl.read_events(level_min=3)['count'] == 0

    tail = tl.read_events(tail=1)
    assert tail['count'] == 1


def test_read_events_out_file(tmp_path):
    _write_log(tmp_path, '1CV8_20230620120000.log', [LINE_OK])
    out = tmp_path / 'ev.json'
    tl = TechLog(tmp_path)
    rep = tl.read_events(out_file=str(out))
    assert out.is_file()
    saved = json.loads(out.read_text(encoding='utf-8'))
    assert saved[0]['event'] == 'SDBL'
    assert rep['count'] == 1


def test_read_events_audit(tmp_path):
    from onec_converter.audit import read_audit, set_audit

    set_audit(tmp_path / 'audit.jsonl')
    _write_log(tmp_path, 'rphost_x.log', [LINE_OK])
    TechLog(tmp_path).read_events()
    recs = read_audit(tmp_path / 'audit.jsonl')
    assert recs[0]['operation'] == 'techlog' and recs[0]['result'] == 'ok'
    set_audit(None)
