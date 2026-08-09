"""Фаза 54: дефекты и чистка аудита раунда 6.

A1  ai_skills.auto_map_schemas — удалён мёртвый код (src_attrs/del).
A2  config.load — strip() строковых значений конфига.
A5  cmd_load (файловый режим) — ошибка при пустом --target вместо
    молчаливого ./load.json.
A7  cmd_audit --csv-out — экранирование формулы Excel ('=', '+', '-', '@').
B5  _table_row_to_rec — единый декодер dump-records/export-xlsx.
B6  DEFAULT_SOURCE_ENCODING константа.
"""
from __future__ import annotations

from pathlib import Path


# ---- A2: config strip ----
def test_config_strips_values(tmp_path: Path, monkeypatch):
    from onec_converter.config import ProjectConfig

    cfg_file = tmp_path / 'onec.toml'
    cfg_file.write_text('[onec]\nsource_encoding = "cp1251"\nlimit = 100\n'
                        'rules_file = " rules.json "\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    cfg = ProjectConfig.load()
    assert cfg.source_encoding == 'cp1251'
    assert cfg.limit == 100
    assert cfg.rules_file == 'rules.json'


def test_config_default_encoding(tmp_path: Path, monkeypatch):
    from onec_converter.config import DEFAULT_SOURCE_ENCODING, ProjectConfig

    monkeypatch.chdir(tmp_path)  # нет onec.toml -> значения по умолчанию
    cfg = ProjectConfig.load()
    assert cfg.source_encoding == DEFAULT_SOURCE_ENCODING == 'cp866'


# ---- A5: load без target ----
def test_load_empty_target_errors(tmp_path, capsys):
    import json as _json

    from onec_converter.cli import cmd_load

    inp = tmp_path / 'input.json'
    inp.write_text(_json.dumps([{'type': 'Справочник.X', 'id': '1',
                                 'key': [], 'attrs': {}, 'refs': {}}]),
                   encoding='utf-8')

    class _A:
        input = str(inp)
        target = ''
        http = ''
        direct = ''
        dry_run = False
        workdir = ''
        snapshot = True
        index_repair = False
        notify_url = ''
        notify_telegram = ''
        source_ib = 'source'
        target_ib = 'target'
        api_key = ''
        token_url = ''
        client_id = ''
        client_secret = ''
        secret = ''
        retries = 0

    rc = cmd_load(_A())
    assert rc == 1
    err = capsys.readouterr().err
    assert '--target, --http или --direct' in err


# ---- A7: CSV-выгрузка экранирует формулы ----
def test_audit_csv_escapes_formula(tmp_path, capsys):
    from onec_converter.audit import AuditLog
    from onec_converter.cli import cmd_audit

    log_path = tmp_path / 'audit.jsonl'
    log = AuditLog(log_path)
    log.info('load', obj='=SUM(A1:A9)', result='ok')
    log.close()
    out = tmp_path / 'audit.csv'

    class _A:
        file = str(log_path)
        level = ''
        op = ''
        obj = ''
        tail = 0
        csv_out = str(out)
        json = False

    rc = cmd_audit(_A())
    assert rc == 0
    body = out.read_text(encoding='utf-8-sig')
    # starts with = -> prefixed by tab, never raw '=SUM'
    assert ',=SUM' not in body and '\t=SUM' in body


# ---- B5: единый декодер возвращает dict/jsonable ----
def test_table_row_to_rec_shared(tmp_path):
    from onec_converter.cli import _table_row_to_rec
    from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd

    t = FixtureTable('_REFERENCE1', fields=[
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=8),
    ])
    t.rows = [encode_row(t.fields, {'_CODE': '0042'})]
    base = tmp_path / 'b'
    base.mkdir()
    write_fake_1cd(base / '1Cv8.1CD', [t])
    from onec_converter.source_8x_file import Database1CD

    with Database1CD(base / '1Cv8.1CD') as db:
        tt = db.tables['_REFERENCE1']
        rec = _table_row_to_rec(next(db.table_rows(tt)), tt)
    assert rec['_CODE'] == '0042'
    assert isinstance(rec, dict)
