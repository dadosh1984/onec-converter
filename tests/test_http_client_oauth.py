"""Фаза 22: OAuth2 client-credentials в HttpClient83 (mock-транспорт)."""

from __future__ import annotations

import httpx
import pytest

from onec_converter.http_client import HttpClient83, HttpServiceError

TOKEN = 'access-token-123'


def _token_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == '/token'
    assert request.headers['content-type'].startswith(
        'application/x-www-form-urlencoded')
    body = request.content.decode()
    assert 'grant_type=client_credentials' in body
    assert 'client_id=cid' in body
    assert 'client_secret=csecret' in body
    return httpx.Response(200, json={'access_token': TOKEN,
                                     'token_type': 'bearer',
                                     'expires_in': 3600})


def _load_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == '/load'
    assert request.headers['authorization'] == f'Bearer {TOKEN}'
    assert 'x-api-key' not in request.headers
    return httpx.Response(200, json={'created': 1, 'updated': 0, 'errors': []})


def _make_transport(token: bool = True) -> httpx.MockTransport:
    return httpx.MockTransport(_token_handler if token else _load_handler)


@pytest.mark.asyncio
async def test_oauth_fetches_token_and_sends_bearer():
    transport = httpx.MockTransport(
        lambda r: _token_handler(r) if r.url.path == '/token' else _load_handler(r))
    client = HttpClient83('http://srv', transport=transport,
                          token_url='http://srv/token',
                          client_id='cid', client_secret='csecret')
    try:
        results = await client.load([{'type': 'Документ.Заказ', 'key': ['1']}],
                                    'src', 'tgt')
    finally:
        await client.aclose()
    assert results[0].created == 1
    assert client._token == TOKEN


@pytest.mark.asyncio
async def test_oauth_token_cached_within_ttl():
    calls = {'n': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/token':
            calls['n'] += 1
            return _token_handler(request)
        return _load_handler(request)

    client = HttpClient83('http://srv', transport=httpx.MockTransport(handler),
                          token_url='http://srv/token', client_id='cid',
                          client_secret='csecret')
    try:
        await client.load([{'type': 'X', 'key': ['1']}], 'src', 'tgt')
        await client.load([{'type': 'X', 'key': ['2']}], 'src', 'tgt')
    finally:
        await client.aclose()
    assert calls['n'] == 1, 'токен запрашивается один раз в пределах TTL'


@pytest.mark.asyncio
async def test_oauth_refreshes_on_401():
    calls = {'token': 0, 'load': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/token':
            calls['token'] += 1
            return _token_handler(request)
        calls['load'] += 1
        if calls['load'] == 1:
            return httpx.Response(401, text='unauthorized')
        return _load_handler(request)

    client = HttpClient83('http://srv', transport=httpx.MockTransport(handler),
                          token_url='http://srv/token', client_id='cid',
                          client_secret='csecret', retries=2)
    try:
        results = await client.load([{'type': 'X', 'key': ['1']}], 'src', 'tgt')
    finally:
        await client.aclose()
    assert calls['token'] == 2, '401 → принудительный refresh токена'
    assert results[0].created == 1


@pytest.mark.asyncio
async def test_fallback_x_api_key_without_token_url():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['key'] = request.headers.get('x-api-key', '')
        seen['auth'] = request.headers.get('authorization', '')
        return httpx.Response(200, json={'created': 0, 'updated': 0, 'errors': []})

    client = HttpClient83('http://srv', transport=httpx.MockTransport(handler),
                          api_key='k123')
    try:
        await client.load([{'type': 'X', 'key': ['1']}], 'src', 'tgt')
    finally:
        await client.aclose()
    assert seen['key'] == 'k123'
    assert seen['auth'] == ''


@pytest.mark.asyncio
async def test_token_endpoint_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='bad client')

    client = HttpClient83('http://srv', transport=httpx.MockTransport(handler),
                          token_url='http://srv/token', client_id='cid',
                          client_secret='csecret')
    try:
        with pytest.raises(HttpServiceError, match='token'):
            await client.metadata()
    finally:
        await client.aclose()
