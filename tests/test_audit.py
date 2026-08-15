"""Фаза 25: audit-логирование миграции — журнал, интеграция, CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from onec_converter.audit import AuditLog, read_audit, set_audit
from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0},
                    {'name': 'Наименование', 'field': '_DESCRIPTION',
                     'type': 'NVC', 'length': 40, 'precision': 0}]},
]}

F_REFERENCE = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]


@pytest.fixture(autouse=True)
def _reset_audit():
    set_audit(None)
    yield
    set_audit(None)


def test_audit_session_context(tmp_path: Path):
    """audit_session изолирует контекст, вложенные сессии работают."""
    from onec_converter.audit import audit_session, get_audit

    with audit_session():
        a_outer = get_audit()
        a_outer.info('test', obj='outer')
        assert a_outer is not None

    # вне контекста — новый in-memory
    a_fallback = get_audit()
    assert a_fallback is not a_outer

    # вложенные контексты
    with audit_session(tmp_path / 'nested.jsonl'):
        a1 = get_audit()
        with audit_session():
            a2 = get_audit()
            assert a2 is not a1
            assert a2.path is None
        # после выхода внутреннего — восстановлен внешний
        assert get_audit() is a1
        assert a1.path == tmp_path / 'nested.jsonl'


# ---- unit: журнал ----
def test_audit_log_file(tmp_path: Path):
    log = AuditLog(tmp_path / 'a.jsonl')
    log.info('extract', obj='Справочник.Банки', guid='G-1', result='ok')
    log.warning('load', obj='Справочник.Банки', detail='нет ссылки')
    log.error('transform', obj='Справочник.Банки', rule='R1', result='error')
    recs = read_audit(tmp_path / 'a.jsonl')
    assert len(recs) == 3
    r = recs[0]
    assert r['level'] == 'INFO' and r['operation'] == 'extract'
    assert r['obj'] == 'Справочник.Банки' and r['guid'] == 'G-1'
    assert r['ts'] and r['result'] == 'ok'
    assert recs[1]['level'] == 'WARN' and recs[2]['level'] == 'ERROR'
    # каждая строка — валидный JSON
    with open(tmp_path / 'a.jsonl', encoding='utf-8') as f:
        for line in f:
            json.loads(line)


def test_audit_invalid_level(tmp_path: Path):
    log = AuditLog(tmp_path / 'x.jsonl')
    with pytest.raises(ValueError):
        log.record('DEBUG', 'op')


# ---- интеграция: load_direct ----
def test_load_direct_writes_audit(tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch):
    from onec_converter.fake_1cd import encode_row
    from onec_converter.load_8x import load_direct
    from onec_converter.write_8x import create_1cd

    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=F_REFERENCE,
                             rows=[encode_row(F_REFERENCE, {
                                 '_IDRREF': b'\x11' * 16,
                                 '_CODE': '00000',
                                 '_DESCRIPTION': 'seed'})])])
    set_audit(tmp_path / 'audit.jsonl')
    rep = load_direct(tgt, [
        {'type': 'Справочник.Банки', 'key': ['00001', 'Банк'],
         'attributes': {'Код': '00001', 'Наименование': 'Банк'},
         'references': {}},
    ], workdir=tmp_path / 'wd')
    assert rep['ok']
    recs = read_audit(tmp_path / 'audit.jsonl')
    loads = [r for r in recs if r['operation'] == 'load']
    assert loads and loads[0]['obj'] == 'Справочник.Банки'
    assert loads[0]['guid']  # GUID приёмника
    assert loads[-1]['obj'] == '1'  # сводное событие total=1


# ---- интеграция: transform ----
def _transform_args(tmp_path: Path, audit: str) -> argparse.Namespace:
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({'version': 1, 'objects': [
        {'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
         'attributes': {'Код': 'Код', 'Наименование': 'Наименование'}},
    ], 'enums': {}}), encoding='utf-8')
    inp = tmp_path / 'in.json'
    inp.write_text(json.dumps([
        {'type': 'Справочник.Банки', 'id': '1', 'key': ['00001', 'A'],
         'attributes': {'Код': '00001', 'Наименование': 'Банк'},
         'references': {}},
        {'type': 'Справочник.Банки', 'id': '2', 'key': ['00002', 'B'],
         'attributes': {'Код': '00002'},  # нет Наименование → TransformError
         'references': {}},
    ]), encoding='utf-8')
    return argparse.Namespace(rules_file=str(rules), input=str(inp),
                              out=str(tmp_path / 'out.json'), preview=0,
                              audit_file=audit)


def test_transform_writes_audit(tmp_path: Path, capsys):
    from onec_converter.cli import cmd_transform

    audit = str(tmp_path / 'audit.jsonl')
    set_audit(audit)
    assert cmd_transform(_transform_args(tmp_path, audit)) == 0  # 1 ок, 1 ошибка
    recs = read_audit(audit)
    assert recs[0]['operation'] == 'transform' and recs[0]['result'] == 'ok'
    assert recs[1]['result'] == 'error' and recs[1]['level'] == 'ERROR'


# ---- интеграция: extract ----
def test_extract_writes_audit(tmp_path: Path):
    from onec_converter.cli import cmd_extract
    from onec_converter.fake_1cd import encode_row

    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE1', fields=F_REFERENCE, rows=[
            encode_row(F_REFERENCE, {'_IDRREF': b'\x01' * 16,
                                     '_CODE': '00001',
                                     '_DESCRIPTION': 'Bank'})])]))
    audit = str(tmp_path / 'audit.jsonl')
    set_audit(audit)
    args = argparse.Namespace(source_dir=str(src), source_encoding='',
                              out=str(tmp_path / 'out.json'),
                              anonymize_fields='', limit=0, objects='',
                              audit_file=audit)
    assert cmd_extract(args) == 0
    recs = read_audit(audit)
    assert recs[0]['operation'] == 'extract'
    assert recs[0]['guid']  # идентификатор записи
    assert recs[0]['result'] == 'ok'


# ---- CLI: audit ----
def test_audit_cli_view(tmp_path: Path, capsys):
    from onec_converter.cli import cmd_audit

    log = AuditLog(tmp_path / 'a.jsonl')
    log.info('load', obj='Справочник.Банки', guid='G1', result='ok')
    log.warning('load', obj='Справочник.Валюты', detail='нет ссылки')
    log.error('transform', obj='Документ.Счёт', result='error')
    args = argparse.Namespace(file=str(tmp_path / 'a.jsonl'), level='',
                              op='', obj='', tail=0, json=False)
    assert cmd_audit(args) == 0
    out, err = capsys.readouterr()
    assert 'Справочник.Банки' in out and 'Документ.Счёт' in out
    counts_line = next(l for l in err.splitlines() if l.startswith('{'))
    counts = json.loads(counts_line)['counts']
    assert counts['INFO'] == 1 and counts['WARN'] == 1
    # фильтры
    args.level = 'ERROR'
    assert cmd_audit(args) == 0
    out2, _ = capsys.readouterr()
    assert 'Справочник.Банки' not in out2 and 'Документ.Счёт' in out2
    # tail
    args.level = ''
    args.tail = 1
    assert cmd_audit(args) == 0
    out3, _ = capsys.readouterr()
    assert 'Документ.Счёт' in out3
