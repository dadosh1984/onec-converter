"""Unit-тесты http-клиента на моке HTTP-сервиса."""
import pytest
import httpx

from onec_converter.http_client import HttpClient83, HttpServiceError, LoadResult

import pytest_asyncio


@pytest.mark.asyncio
async def test_metadata_success(monkeypatch):
    async def fake_request(self, method, path, json=None):
        return {'Справочники': []}
    monkeypatch.setattr(HttpClient83, '_request', fake_request)
    c = HttpClient83('http://localhost:8080')
    try:
        meta = await c.metadata()
        assert 'Справочники' in meta
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_load_batches(monkeypatch):
    calls = []

    async def fake_request(self, method, path, json=None):
        calls.append(json)
        return {'ok': True, 'created': len(json['objects']), 'updated': 0, 'errors': []}

    monkeypatch.setattr(HttpClient83, '_request', fake_request)
    c = HttpClient83('http://localhost:8080', batch_size=2)
    try:
        objs = [{'type': f'Справочник.X{i}'} for i in range(5)]
        results = await c.load(objs, 'src', 'tgt')
        assert len(calls) == 3
        assert sum(r.created for r in results) == 5
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_http_error_raises():
    class Boom(HttpClient83):
        async def _request(self, method, path, json=None):
            raise HttpServiceError('409')
    with pytest.raises(HttpServiceError):
        await Boom('http://x').metadata()
