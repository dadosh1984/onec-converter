"""Фаза 33: локальный JWT-контур (mint-token + http_client secret + BSL согласование)."""

from __future__ import annotations

import httpx
import pytest

from onec_converter.http_client import HttpClient83
from onec_converter.jwt_auth import JwtError, mint_jwt, verify_jwt

SECRET = 'test-shared-secret'
ISSUER = 'onec-converter'


# ---- mint-token CLI ----
def test_mint_token_cli(capsys, monkeypatch):
    import argparse

    from onec_converter.cli import cmd_mint_token

    args = argparse.Namespace(secret=SECRET, issuer=ISSUER, exp_min=60)
    rc = cmd_mint_token(args)
    out = capsys.readouterr().out.strip()
    assert rc == 0
    # токен валиден и проходит проверку
    payload = verify_jwt(out, SECRET, ISSUER)
    assert payload['iss'] == ISSUER


def test_mint_token_cli_requires_secret(capsys):
    import argparse

    from onec_converter.cli import cmd_mint_token

    rc = cmd_mint_token(argparse.Namespace(secret='', issuer=ISSUER, exp_min=1))
    assert rc == 1
    assert '--secret' in capsys.readouterr().err


# ---- BSL-согласование: логика ПроверитьJWT воспроизведена по схеме Module.bsl ----
def test_mint_matches_bsl_verifier():
    """Токен, выпущенный mint_jwt, проходит BSL-логику ПроверитьJWT
    (base64url + alg=HS256 + exp/iss + HMAC-SHA256 подпись на общем секрете)."""
    import base64
    import hashlib
    import hmac
    import json
    import time

    token = mint_jwt(SECRET, ISSUER, 3600)
    header_b64, payload_b64, sig_b64 = token.split('.')

    # декодирование base64url (как в BSL ДекодироватьBase64URL)
    def b64u_decode(s: str) -> bytes:
        pad = '=' * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + pad)

    header = json.loads(b64u_decode(header_b64))
    payload = json.loads(b64u_decode(payload_b64))
    # проверки modulo БSL
    assert header['alg'] == 'HS256'
    assert 'exp' in payload and 'iss' in payload
    assert time.time() < payload['exp']
    assert payload['iss'] == ISSUER
    # подпись HMAC-SHA256 как в Module.bsl::HMACSHA256
    sig = b64u_decode(sig_b64)
    expected = hmac.new(SECRET.encode(), f'{header_b64}.{payload_b64}'.encode(),
                        hashlib.sha256).digest()
    assert hmac.compare_digest(expected, sig)
    # и итоговая проверка верификатором
    assert verify_jwt(token, SECRET, ISSUER)


def test_mint_rejects_wrong_secret_on_bsl():
    """Токен секрета A отвергается приёмником с секретом Б."""
    token = mint_jwt('A', ISSUER, 60)
    with pytest.raises(JwtError, match='подпись'):
        verify_jwt(token, 'B', ISSUER)


# ---- http_client: secret-режим (локальный mint-token) ----
def _load_handler(request: httpx.Request) -> httpx.Response:
    auth = request.headers.get('authorization', '')
    assert auth.startswith('Bearer ')
    token = auth[len('Bearer '):]
    assert verify_jwt(token, SECRET, ISSUER)
    return httpx.Response(200, json={'created': 1, 'updated': 0, 'errors': []})


@pytest.mark.asyncio
async def test_client_secret_sends_local_jwt():
    transport = httpx.MockTransport(_load_handler)
    client = HttpClient83('https://h', transport=transport,
                          secret=SECRET, issuer=ISSUER)
    res = await client.load([{'objs': 'x'}], 'source', 'target')
    await client.aclose()
    assert res and res[0].created == 1


@pytest.mark.asyncio
async def test_client_secret_uses_bare_bearer(monkeypatch):
    captured: dict[str, str | None] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured['auth'] = request.headers.get('authorization')
        captured['x'] = request.headers.get('x-api-key')
        return httpx.Response(200, json={
            'created': 0, 'updated': 0, 'errors': []})

    transport = httpx.MockTransport(capture)
    client = HttpClient83('https://h', transport=transport,
                          secret=SECRET, issuer=ISSUER)
    await client.load([{'objs': 'x'}], 'source', 'target')
    await client.aclose()
    assert captured['auth'] and captured['auth'].startswith('Bearer ')
    assert captured['x'] is None  # secret-режим не шлёт X-API-Key
    token = captured['auth'][len('Bearer '):]
    assert verify_jwt(token, SECRET, ISSUER)


