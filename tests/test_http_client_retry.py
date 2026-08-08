"""Фаза 18: retry 5xx и осмысленные ошибки в http_client."""
from __future__ import annotations

import httpx
import pytest

from onec_converter.http_client import HttpClient83, HttpServiceError


def _client(responses: list[httpx.Response]):
    """HttpClient83 с записанным списком ответов по порядку."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return responses.pop(0) if responses else httpx.Response(500)

    transport = httpx.MockTransport(handler)
    c = HttpClient83('http://x', transport=transport, retries=3)
    return c, calls


@pytest.mark.asyncio
async def test_5xx_retries_with_backoff():
    """500 ретраится 3 раза (все попытки), затем осмысленная ошибка с кодом."""
    resp = [httpx.Response(500, text='boom'),
            httpx.Response(500, text='boom'),
            httpx.Response(500, text='boom')]
    c, calls = _client(resp)
    try:
        with pytest.raises(HttpServiceError, match='500'):
            await c.metadata()
    finally:
        await c.aclose()
    assert len(calls) == 3  # все ретраи


@pytest.mark.asyncio
async def test_5xx_then_success_nonzero_backoff():
    """500 → сон → 200 (после backoff)."""
    import asyncio
    real_sleep = asyncio.sleep
    delays: list[float] = []

    async def fake_sleep(d: float) -> None:
        delays.append(d)
    # поверх: заменим sleep только на время синхронного прогона
    asyncio.sleep = fake_sleep  # type: ignore[assignment]
    try:
        resp = [httpx.Response(500, text='x'), httpx.Response(200, text='{}')]
        c, _calls = _client(resp)
        try:
            out = await c.metadata()
            assert out == {}
            assert delays and delays[0] > 0  # backoff был ненулевой
        finally:
            await c.aclose()
    finally:
        asyncio.sleep = real_sleep  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_4xx_no_retry():
    """404 — клиентская ошибка, без retry, осмысленное сообщение с кодом/телом."""
    c, calls = _client([httpx.Response(404, text='not found'), httpx.Response(200)])
    try:
        with pytest.raises(HttpServiceError, match='404'):
            await c.metadata()
    finally:
        await c.aclose()
    assert len(calls) == 1  # без ретрая


@pytest.mark.asyncio
async def test_transport_error_retries():
    """Timeout — транспортная ошибка, ретраится, final с текстом причины."""
    import httpx as _httpx

    class ErrTransport(_httpx.AsyncBaseTransport):
        async def handle_async_request(
                self, request: _httpx.Request
        ) -> _httpx.Response:
            raise _httpx.ConnectError('could not connect')

    c = HttpClient83('http://x', transport=ErrTransport(), retries=2)
    try:
        with pytest.raises(HttpServiceError, match='transport'):
            await c.metadata()
    finally:
        await c.aclose()
