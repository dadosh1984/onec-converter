"""Фаза 52 (0.35.0): Безопасность — U8/U27/U28/U29/U30/U31/U32/U33.

- U8/U27: mask_secrets (userinfo, key=) в DSN/URL; sql_source маскирует
  исключения; secret_mask.py
- U28: s3 assume_role (STS Signed POST via mock)
- U29/U32: BSL лимит пакета (413) + идемпотентность объектов по idem;
  client replace=true (идемпотентность сетевых ретраев)
- U30: jwt kid/ротация — mint с kid, verify_jwt_kid по набору секретов
- U31: pre-commit секрет-сканер (строгие паттерны в .githooks/pre-commit)
- U33: notify ретрай 5xx (транзиентные шлюзы)
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BSL = ROOT / 'src/onec_converter/extension_83/Module.bsl'


# ---------------------------------------------------------------------------
# U8/U27: маскирование секретов
# ---------------------------------------------------------------------------

def test_mask_secrets_userinfo_and_keyvalue():
    from onec_converter.secret_mask import mask_secrets

    assert mask_secrets('postgresql://user:supersecret@host/db') == \
        'postgresql://user:***@host/db'
    assert mask_secrets('http://a:b@h/') == 'http://a:***@h/'
    assert 'tok123' not in mask_secrets('x=1&token=tok123&y=2')
    assert 'sk12' not in mask_secrets('client_secret=sk12')
    assert mask_secrets('просто текст без секретов') == 'просто текст без секретов'
    assert 'ABC' not in mask_secrets('password=ABC&u=1')


def test_mask_dsn_used_in_sql_source_error(monkeypatch):
    from onec_converter.sql_source import GenericSqlSource, SqlSourceError

    dsn = 'postgresql://u:heavysecret@srv/db'

    class BadDriver:
        def connect(self, *a: object, **k: object) -> object:
            raise RuntimeError(dsn)

    src = GenericSqlSource('postgres', dsn, BadDriver())
    with pytest.raises(SqlSourceError) as ei:
        src._connect()
    assert 'heavysecret' not in str(ei.value)
    assert '***' in str(ei.value) or 'не удалось' in str(ei.value)


# ---------------------------------------------------------------------------
# U28: s3 STS AssumeRole
# ---------------------------------------------------------------------------

def test_s3_assume_role_sets_session_name(monkeypatch):
    from onec_converter import s3_client

    calls: dict[str, object] = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a: object) -> None:
            return None

        def read(self) -> bytes:
            return (b'<AssumeRoleResponse xmlns="https://sts.amazonaws.com/'
                    b'doc/2011-06-15/"><AssumeRoleResult><Credentials>'
                    b'<AccessKeyId>AKID</AccessKeyId>'
                    b'<SecretAccessKey>SEC</SecretAccessKey>'
                    b'<SessionToken>TOK</SessionToken>'
                    b'</Credentials></AssumeRoleResult>'
                    b'</AssumeRoleResponse>')

    import urllib.request

    def fake_urlopen(req: object, timeout: int = 30) -> FakeResp:
        calls['url'] = getattr(req, 'full_url', str(req))
        calls['data'] = getattr(req, 'data', b'') or b''
        return FakeResp()

    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)
    creds = s3_client.assume_role('arn:aws:iam::123:role/x', 'sess',
                                  access_key='AK', secret_key='SK')
    assert creds['AccessKeyId'] == 'AKID'
    body = calls['data'].decode() if isinstance(calls['data'], bytes) else ''
    assert 'AssumeRole' in body and 'sess' in body


def test_s3_assume_role_no_keys():
    from onec_converter.s3_client import S3Error, assume_role

    with pytest.raises(S3Error):
        assume_role('arn:x', 's', access_key='', secret_key='')


# ---------------------------------------------------------------------------
# U29/U32: BSL лимит пакета и идемпотентность
# ---------------------------------------------------------------------------

def test_bsl_package_limit_marker():
    text = BSL.read_text(encoding='utf-8-sig')
    assert 'ЛимитПакета = 1000' in text
    assert '413' in text  # HTTP 413 Payload Too Large
    assert 'слишком много объектов' in text


def test_bsl_idempotency_marker():
    text = BSL.read_text(encoding='utf-8-sig')
    assert 'ИдемпотентностьКлюч' in text
    assert 'ОбработанныеКлючи' in text
    assert 'Продолжить' in text  # повторный объект с тем же idem пропускается


# ---------------------------------------------------------------------------
# U30: JWT kid/ротация
# ---------------------------------------------------------------------------

def test_jwt_kid_rotation():
    import time

    from onec_converter.jwt_auth import JwtError, mint_jwt, verify_jwt_kid

    now = time.time()
    key_old = mint_jwt('oldsecret', 'onec', 300, now=now, kid='prev-1')
    key_new = mint_jwt('newsecret', 'onec', 300, now=now, kid='current')

    secrets = {'prev-1': 'oldsecret', 'current': 'newsecret'}
    # текущий kid — своим секретом
    assert verify_jwt_kid(key_new, secrets, 'onec', now=now)['iss'] == 'onec'
    # плавная ротация: старый kid всё ещё валиден
    assert verify_jwt_kid(key_old, secrets, 'onec', now=now)['iss'] == 'onec'

    # жёсткость: токен с kid, секрет которого отсутствует — отклонён
    bad = mint_jwt('unknown', 'onec', 300, now=now, kid='missing')
    try:
        verify_jwt_kid(bad, secrets, 'onec', now=now)
        raise AssertionError('ожидали JwtError')
    except JwtError:
        pass

    # обратная совместимость: токен без kid проверяется любым секретом
    legacy = mint_jwt('newsecret', 'onec', 300, now=now)
    assert verify_jwt_kid(legacy, secrets, 'onec', now=now)['iss'] == 'onec'


def test_bsl_jwt_rotation_marker():
    text = BSL.read_text(encoding='utf-8-sig')
    assert 'НаборСекретовJWT' in text
    assert 'kid' in text and 'ПроверитьJWT' in text


# ---------------------------------------------------------------------------
# U31: pre-commit секрет-сканер
# ---------------------------------------------------------------------------

def test_precommit_secret_scanner_rule():
    hook = (ROOT / '.githooks/pre-commit').read_text(encoding='utf-8')
    assert 'AKIA' in hook  # AWS key pattern
    assert 'PRIVATE KEY' in hook or 'private key' in hook.lower()
    assert 'client_secret' in hook


# ---------------------------------------------------------------------------
# U33: notify ретрай 5xx
# ---------------------------------------------------------------------------

def test_notify_retries_5xx_then_succeeds(tmp_path: Path):
    import http.server
    import threading

    from onec_converter.notify import send_webhook

    state = {'calls': 0}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', '0')))
            state['calls'] += 1
            if state['calls'] == 1:
                self.send_response(502)  # транзиентный сбой шлюза
            else:
                self.send_response(200)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        res = send_webhook(f'http://127.0.0.1:{port}/h', {'a': 1},
                           attempts=3, backoff=0.01)
        assert res['ok'] is True
        assert state['calls'] == 2  # 502 -> ретрай -> 200
    finally:
        srv.shutdown()
        t.join()


def test_notify_5xx_all_fail(tmp_path: Path):
    import http.server
    import threading

    from onec_converter.notify import NotifyError, send_webhook

    state = {'calls': 0}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', '0')))
            state['calls'] += 1
            self.send_response(503)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        with pytest.raises(NotifyError):
            send_webhook(f'http://127.0.0.1:{port}/h', {}, attempts=2,
                         backoff=0.01)
        assert state['calls'] == 2
    finally:
        srv.shutdown()
        t.join()
