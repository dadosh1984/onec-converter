"""Фаза 50 (0.33.0): покрытие и тесты — U43/U44/U47/U48/U49/U50.

- U43: 9 модулей добавлены в coverage_modules (pyproject)
- U44: dedicated-тесты kd3_export/sonar_report/gdpr_152_report/notify/
       terminal/strict/type_priority (s3_client/source_techlog уже покрыты)
- U47: property round-trip 1CD (build_fake_1cd -> Database1CD -> обратно)
- U50: hypothesis fuzz кеша (Cache round-trip) и SQL-драйверов
"""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# U43: модули в coverage-конфиге
# ---------------------------------------------------------------------------


def test_coverage_modules_include_nine_new():
    import tomllib

    cfg = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
    mods = cfg['tool']['onec-gates']['coverage_modules']
    for m in ('kd3_export', 'sonar_report', 'gdpr_152_report',
              'source_techlog', 'notify', 'terminal', 'strict',
              'type_priority'):
        assert m in mods, f'{m} не в coverage_modules'
    assert cfg['tool']['onec-gates']['coverage_threshold'] >= 70


# ---------------------------------------------------------------------------
# U44: kd3_export
# ---------------------------------------------------------------------------


def test_kd3_export_writes_file(tmp_path: Path):
    from onec_converter.kd3_export import export_kd3

    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({
        'version': 1,
        'enums': {'Мужской': 'M'},
        'objects': [{'source': 'Справочник.Банки',
                     'target': 'Справочник.Банки',
                     'attributes': {'Наименование': 'Описание'}}],
    }, ensure_ascii=False), encoding='utf-8')
    out = tmp_path / 'kd3.xml'
    rep = export_kd3(rules, str(out))
    assert rep['ok'] is True and rep['rules'] == 1 and rep['enums'] == 1
    xml = out.read_text(encoding='utf-8')
    assert 'DataContainer' in xml and 'Rule' in xml and 'EnumMappings' in xml


def test_kd3_export_errors(tmp_path: Path):
    from onec_converter.kd3_export import Kd3Error, export_kd3

    with pytest.raises(Kd3Error):
        export_kd3(tmp_path / 'nope.json')
    bad = tmp_path / 'bad.json'
    bad.write_text('{not json', encoding='utf-8')
    with pytest.raises(Kd3Error):
        export_kd3(bad)
    wrong = tmp_path / 'wrong.json'
    wrong.write_text('{"version": 2, "objects": []}', encoding='utf-8')
    with pytest.raises(Kd3Error):
        export_kd3(wrong)


# ---------------------------------------------------------------------------
# U44: sonar_report
# ---------------------------------------------------------------------------


def test_sonar_one_issue_mapping():
    from onec_converter.sonar_report import _severity, one_issue

    it = one_issue('RUF022', 'a.py', 3, 'msg')
    assert it['ruleId'] == 'RU022' and it['line'] == 3 and it['severity'] == 'MINOR'
    assert one_issue('F401', 'b.py', 1, 'm')['severity'] == 'MAJOR'
    assert one_issue('E501', 'c.py', 1, 'm')['severity'] == 'MAJOR'
    assert one_issue('PLW1510', 'd.py', 1, 'm')['ruleId'] == 'PLW1510'
    assert _severity('X') == 'MINOR'


def test_sonar_report_with_fake_ruff(tmp_path: Path):
    from onec_converter.sonar_report import sonar_report

    fake = tmp_path / 'fake_ruff.py'
    fake.write_text(
        'import json,sys\n'
        'print(json.dumps([{"code":"F401","filename":"x.py",'
        '"location":{"row":5},"message":"unused"}]))\n',
        encoding='utf-8')
    rep = sonar_report('src', fmt='json', ruff_cmd=['python', str(fake)])
    assert rep['ok'] and rep['total'] == 1
    assert rep['issues'][0]['ruleId'] == 'F401'
    assert json.loads(rep['body'])[0]['severity'] == 'MAJOR'
    xml_rep = sonar_report('src', fmt='xml', ruff_cmd=['python', str(fake)])
    assert '<issue ' in xml_rep['body']
    from onec_converter.sonar_report import SonarReportError
    with pytest.raises(SonarReportError):
        sonar_report('src', fmt='yaml')


# ---------------------------------------------------------------------------
# U44: gdpr_152_report
# ---------------------------------------------------------------------------


def _audit_line(ts: str, op: str, **extra: object) -> str:
    rec = {'ts': ts, 'level': 'info', 'operation': op,
           'obj': '', 'guid': '', 'rule': '', 'result': 'ok',
           'hash': 'aa', 'prev_hash': 'bb'}
    rec.update(extra)
    return json.dumps(rec, ensure_ascii=False)


def test_gdpr_report_basic(tmp_path: Path):
    from onec_converter.gdpr_152_report import gdpr_report

    af = tmp_path / 'audit.jsonl'
    af.write_text(_audit_line('2026-01-01T00:00:00', 'anonymize') + '\n',
                  encoding='utf-8')
    rep = gdpr_report(af)
    assert rep['ok'] and rep['generated'] == 1 and rep['tamper_evident'] is True
    assert 'RU' in rep['profile']


def test_gdpr_report_rules_and_errors(tmp_path: Path):
    from onec_converter.gdpr_152_report import PiiReportError, gdpr_report

    with pytest.raises(PiiReportError):
        gdpr_report(tmp_path / 'nope.jsonl')
    af = tmp_path / 'a.jsonl'
    af.write_text(_audit_line('2026-01-01T00:00:00', 'load') + '\n',
                  encoding='utf-8')
    with pytest.raises(PiiReportError):
        gdpr_report(af, rules_file=tmp_path / 'nope.json')
    bad = tmp_path / 'bad.json'
    bad.write_text('x', encoding='utf-8')
    with pytest.raises(PiiReportError):
        gdpr_report(af, rules_file=bad)
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({'objects': [{'attributes': {
        'ФИО': {}, 'НомерТелефона': {}}}]}), encoding='utf-8')
    rep = gdpr_report(af, rules_file=rules)
    assert rep['pii_fields']  # ПДн-поля из правил найдены


def test_gdpr_report_no_hashes(tmp_path: Path):
    from onec_converter.gdpr_152_report import gdpr_report

    af = tmp_path / 'a.jsonl'
    af.write_text('{"ts":"t","level":"i","operation":"x"}\n', encoding='utf-8')
    assert gdpr_report(af)['tamper_evident'] is False


# ---------------------------------------------------------------------------
# U44: notify
# ---------------------------------------------------------------------------


def test_notify_webhook_success(tmp_path: Path):
    import http.server
    import threading

    from onec_converter.notify import send_webhook

    received: dict[str, object] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get('Content-Length', '0'))
            received['body'] = json.loads(self.rfile.read(n))
            received['path'] = self.path
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

        def log_message(self, *args: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        rep = send_webhook(f'http://127.0.0.1:{port}/hook',
                           {'text': 'привет'}, attempts=1)
        assert rep['ok'] is True
        assert received['body'] == {'text': 'привет'}
        assert received['path'] == '/hook'
    finally:
        srv.shutdown()
        t.join()


def test_notify_telegram_bad_chat():
    from onec_converter.notify import telegram_url

    url = telegram_url('tok/en', 'chat id')
    assert 'tok%2Fen' in url and 'chat%20id' in url  # экранирование (Фаза 46)
    assert url.startswith('https://api.telegram.org/bot')


# ---------------------------------------------------------------------------
# U44: terminal (stderr-эмиссия)
# ---------------------------------------------------------------------------


def test_terminal_emits_to_stderr(capsys):
    from onec_converter.terminal import (
        playbook_step,
        tool_error,
        tool_finished,
        tool_started,
    )

    tool_started('table_sizes', "('base', 'Ref')")
    tool_finished('table_sizes', True, 62.4, '300 таблиц')
    tool_error('query_table', 1.2, 'нет таблицы')
    playbook_step(1, 3, 'extract')
    out, err = capsys.readouterr()
    assert out == ''
    assert '[onec-converter' in err
    assert '▶ table_sizes' in err and '✔ table_sizes' in err
    assert '✘ query_table' in err and 'шаг 1/3' in err


def test_terminal_tool_summary():
    from onec_converter.terminal import tool_summary

    assert tool_summary({'a': 1, 'ok': True}) == 'ok=True'
    assert tool_summary('{"x": 2}') == "{'x': 2}"
    assert tool_summary('не-json') == 'не-json'


# ---------------------------------------------------------------------------
# U44: strict
# ---------------------------------------------------------------------------


def _fm(name: str, ftype: str, length: int = 0, precision: int = 0):
    from types import SimpleNamespace

    return SimpleNamespace(name=name, ftype=ftype, length=length,
                           precision=precision)


def test_strict_validate_value():
    from onec_converter.strict import validate_value

    assert validate_value('NVC', 5, 0, 'корот') == []
    assert validate_value('NVC', 3, 0, 'длинное') != []
    assert validate_value('NC', 2, 0, 'abc') != []
    assert validate_value('N', 4, 0, 'abc') != []
    assert validate_value('N', 4, 0, 123) == []
    assert validate_value('N', 2, 0, 9999) != []
    assert validate_value('DT', 0, 0, '20260101120000') == []
    assert validate_value('DT', 0, 0, '20260101') == []
    assert validate_value('DT', 0, 0, '20261301') != []
    assert validate_value('DT', 0, 0, 'не дата') != []
    assert validate_value('B', 0, 0, b'\x01' * 16) == []
    assert validate_value('B', 0, 0, b'\x01') != []
    assert validate_value('RV', 0, 0, '11111111-2222-3333-4444-555555555555') == []
    assert validate_value('RV', 0, 0, 'не-guid') != []
    assert validate_value('RV', 0, 0, 'Справочник.Банки:1') == []
    assert validate_value('RV', 0, 0, 42) != []
    assert validate_value('XYZ', 0, 0, 'v') == []


def test_strict_validate_object():
    from onec_converter.strict import StrictReport, validate_object

    rep = validate_object({'type': 'Справочник', 'attributes': {
        'Имя': 'очень длинное значение'}}, [_fm('Имя', 'NVC', 5)])
    assert not rep.ok and rep.errors
    assert isinstance(rep.as_dict()['errors'], list)
    assert StrictReport().ok is True
    assert validate_object({'attributes': {'Имя': 'ок'}},
                           [_fm('Имя', 'NVC', 5)]).ok is True


# ---------------------------------------------------------------------------
# U44: type_priority
# ---------------------------------------------------------------------------


def test_type_priority_extended():
    from onec_converter.type_priority import resolve_type_priority, type_rank

    assert type_rank('unknown') == 5
    assert type_rank('неизвестный') == 5
    assert resolve_type_priority(['string', 'string']) == 'string'
    assert resolve_type_priority(['ref', 'bool', 'date']) == 'date'
    assert resolve_type_priority(['unknown', 'ref']) == 'ref'


# ---------------------------------------------------------------------------
# U47: property round-trip 1CD
# ---------------------------------------------------------------------------


def test_roundtrip_fake_1cd_property(tmp_path: Path):
    """Случайная (seeded) база: build_fake_1cd -> Database1CD -> те же таблицы."""
    from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
    from onec_converter.source_8x_file import Database1CD

    rng = random.Random(20260809)
    tables: list[FixtureTable] = []
    for i in range(3):
        fields = [FixtureField('_IDRREF', 'B', length=16),
                  FixtureField('_VERSION', 'RV', length=16)]
        for j in range(rng.randint(0, 4)):
            fields.append(FixtureField(
                f'F{j}', rng.choice(['S', 'N', 'DT']),
                length=rng.choice([5, 10, 20])))
        n_rows = rng.randint(1, 5)
        rows: list[bytes] = []
        for _ in range(n_rows):
            vals: dict[str, object] = {
                '_IDRREF': b'\x00' * 16, '_VERSION': b'\x00' * 16}
            for f in fields:
                if f.name.startswith('F'):
                    if f.type == 'N':
                        vals[f.name] = rng.randint(0, 999)
                    elif f.type == 'DT':
                        vals[f.name] = '20260101120000'
                    else:
                        vals[f.name] = ''.join(
                            rng.choice(string.ascii_letters)
                            for _ in range(rng.randint(1, 3)))
            rows.append(encode_row(fields, vals))
        tables.append(FixtureTable(f'_REF{i}', fields=fields, rows=rows))

    cd = tmp_path / 'rt' / '1Cv8.1CD'
    (tmp_path / 'rt').mkdir()
    cd.write_bytes(build_fake_1cd(tables))
    with Database1CD(cd) as db:
        assert set(db.tables) == {t.name for t in tables}
        for t in tables:
            td = db.tables[t.name]
            assert list(td.fields) == [f.name for f in t.fields]
            got = list(db.table_rows(td))
            assert len(got) == len(t.rows)


# ---------------------------------------------------------------------------
# U50: hypothesis fuzz
# ---------------------------------------------------------------------------

hypothesis = pytest.importorskip('hypothesis')
from hypothesis import given, settings
from hypothesis import strategies as st


@given(st.binary(min_size=0, max_size=4096),
       st.text(alphabet='abc123-_', min_size=1, max_size=32))
@settings(max_examples=40, deadline=None)
def test_cache_put_get_roundtrip_fuzz(data: bytes, key: str):
    from onec_converter.cache import Cache

    c = Cache(root=Path('.fuzz_cache_tmp'))
    try:
        p = c.put(key, 'blob', data)
        assert p.read_bytes() == data
        assert c.has(key, 'blob')
        got = c.get(key, 'blob')
        assert got is not None and got.read_bytes() == data
    finally:
        import shutil

        shutil.rmtree('.fuzz_cache_tmp', ignore_errors=True)


@given(st.one_of(st.none(), st.booleans(), st.integers(min_value=-10 ** 12,
                                                       max_value=10 ** 12),
                 st.floats(allow_nan=False, allow_infinity=False),
                 st.text(max_size=40), st.lists(st.integers(), max_size=8)))
@settings(max_examples=40, deadline=None)
def test_strict_number_fuzz(value: object):
    from onec_converter.strict import validate_value

    errs = validate_value('N', 18, 2, value)
    assert isinstance(errs, list)
    if isinstance(value, (int, float)) and abs(value) < 10 ** 17:
        assert errs == []
