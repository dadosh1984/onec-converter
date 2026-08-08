"""Фаза 27: мониторинг и интеграции — health, S3, уведомления."""
from __future__ import annotations

import datetime
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd
from onec_converter.s3_client import S3Error, put_object, sign_v4

F = [FixtureField('_VERSION', 'RV', length=16),
     FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]


@pytest.fixture
def fake_db(tmp_path: Path) -> Path:
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE1', fields=F, rows=[])]))
    return src


# ---- health ----
def test_base_health(fake_db: Path):
    from onec_converter.health import base_health

    h = base_health(fake_db, include_rows=True)
    assert h['ok']
    assert h['tables'] >= 1 and h['rows'] >= 0
    assert h['rows_computed'] is True
    assert h['version'] and h['free_bytes'] > 0
    assert h['file_bytes'] > 0 and h['page_size'] > 0
    assert h['locks'] == []  # нет lock-файлов на синтетике


def test_health_lock_files(fake_db: Path):
    from onec_converter.health import base_health

    (fake_db / '1Cv8.1CL').write_bytes(b'x')
    h = base_health(fake_db)
    assert h['locks'] == ['1Cv8.1CL']


def test_health_missing(fake_db: Path):
    from onec_converter.health import HealthError, base_health

    with pytest.raises(HealthError):
        base_health(fake_db / 'нет')


# ---- S3: SigV4 по каноническому AWS-вектору ----
def test_sign_v4_matches_aws_reference():
    # Эталон: канонический пример AWS SigV4 (PUT /test%20file.txt,
    # payload b'Welcome to Amazon S3.', дата 20130524) — сверен с
    # клиентом botocore (S3SigV4Auth): Signature=5f76a867... эквивалентна.
    auth, amz_date, payload_hash = sign_v4(
        'AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
        method='PUT', path='/test%20file.txt',
        host='examplebucket.s3.amazonaws.com', payload=b'Welcome to Amazon S3.',
        now=datetime.datetime(2013, 5, 24, tzinfo=datetime.UTC))
    assert amz_date == '20130524T000000Z'
    assert payload_hash == (
        '44ce7dd67c959e0d3524ffac1771dfbba87d2b6b4b4e99e42034a8b803f8b072')
    assert auth.endswith(
        'Signature=5f76a8670176f81a92f0d44e0c8f1183ff2c686799714737e39a0b65'
        'aeec3602')


def test_put_object_no_keys():
    with pytest.raises(S3Error, match='ключ'):
        put_object('b', 'k', b'{}', access_key='', secret_key='',
                   endpoint='http://127.0.0.1:9')


# ---- S3: интеграция с mock-сервером ----
class _Rec:
    auth: str = ''
    body: bytes = b''
    path: str = ''


def _run_s3_mock(rec: _Rec):
    class H(BaseHTTPRequestHandler):
        def do_PUT(self):
            rec.path = self.path
            rec.auth = self.headers.get('Authorization', '')
            n = int(self.headers.get('Content-Length', '0'))
            rec.body = self.rfile.read(n)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_put_object_to_endpoint():
    rec = _Rec()
    srv = _run_s3_mock(rec)
    port = srv.server_address[1]
    try:
        rep = put_object('bkt', 'report.json', b'{"ok": true}',
                         access_key='AK', secret_key='SK',
                         endpoint=f'http://127.0.0.1:{port}')
        assert rep['ok'] and rep['key'] == 'report.json'
        assert rec.body == b'{"ok": true}'
        assert 'AWS4-HMAC-SHA256' in rec.auth
        assert rec.path == '/bkt/report.json'
    finally:
        srv.shutdown()


# ---- уведомления: webhook-mock ----
def _run_webhook_mock(rec: _Rec):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get('Content-Length', '0'))
            rec.body = self.rfile.read(n)
            rec.path = self.path
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_send_webhook():
    from onec_converter.notify import send_webhook

    rec = _Rec()
    srv = _run_webhook_mock(rec)
    port = srv.server_address[1]
    try:
        res = send_webhook(f'http://127.0.0.1:{port}/hook', {'ok': True,
                                                             'total': 3})
        assert res['ok']
        assert json.loads(rec.body) == {'ok': True, 'total': 3}
    finally:
        srv.shutdown()


def test_telegram_url():
    from onec_converter.notify import telegram_url

    url = telegram_url('TOKEN', '-100123')
    assert url == ('https://api.telegram.org/botTOKEN/sendMessage'
                   '?chat_id=-100123')


# ---- CLI: dump-report и notify ----
def test_cli_dump_report(fake_db: Path, tmp_path: Path, capsys):
    from onec_converter.cli import cmd_dump_report

    rep = tmp_path / 'report.json'
    rep.write_text('{"ok": true}', encoding='utf-8')
    import argparse
    args = argparse.Namespace(file=str(rep), s3='bkt', key='', secret='',
                              endpoint='', region='us-east-1')
    # нет ключей -> rc=1 с понятным сообщением
    assert cmd_dump_report(args) == 1
    err = capsys.readouterr().err
    assert 'ключ' in err


def test_cli_load_notify_webhook(tmp_path: Path, capsys):
    from onec_converter.cli import cmd_load

    inp = tmp_path / 'batch.json'
    inp.write_text(json.dumps([{'type': 'Справочник.Банки', 'id': '1',
                                'key': [], 'attributes': {},
                                'references': {}}]), encoding='utf-8')
    rec = _Rec()
    srv = _run_webhook_mock(rec)
    port = srv.server_address[1]
    try:
        import argparse
        args = argparse.Namespace(input=str(inp), target=str(tmp_path),
                                  http='', direct='', workdir='',
                                  no_snapshot=False, source_ib='source',
                                  notify_url=f'http://127.0.0.1:{port}/h',
                                  notify_telegram='')
        assert cmd_load(args) == 0
        payload = json.loads(rec.body)
        assert payload['ok'] and payload['mode'] == 'file'
    finally:
        srv.shutdown()


def test_cli_load_notify_telegram_format():
    import argparse

    from onec_converter.cli import _notify

    args = argparse.Namespace(notify_url='', notify_telegram='token')  # без :
    _notify(args, {'ok': True})  # best-effort: не бросает
