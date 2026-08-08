"""Тесты HTTP-источника."""
import pytest

from onec_converter.http_client import HttpClient83
from onec_converter.source_http import HttpSource83


@pytest.mark.asyncio
async def test_http_source_objects(monkeypatch):
    async def fake_request(self, method, path, json=None):
        return {'objects': [{'type': 'Справочник.Банки'}]}
    monkeypatch.setattr(HttpClient83, '_request', fake_request)
    src = HttpSource83(HttpClient83('http://x'))
    objs = await src.objects('Справочник.Банки')
    assert len(objs) == 1
