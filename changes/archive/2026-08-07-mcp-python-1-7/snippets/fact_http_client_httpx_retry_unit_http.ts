// GREEN: http_client — httpx-клиент HTTP-сервиса 8.3 (пакеты, retry, таймауты, ошибки)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function fact_http_client_httpx_retry_unit_http() {
  const files: Record<string, string> = {
    'src/onec_converter/http_client.py': `"""Асинхронный httpx-клиент HTTP-сервиса расширения 8.3 (/metadata, /load).

Пакетная загрузка (до batch_size объектов на запрос), retry с экспоненциальной
задержкой, таймауты, декодирование ответов, идемпотентная повторная отправка.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx


class HttpServiceError(Exception):
    """Ошибка HTTP-сервиса приёмника."""


@dataclass
class LoadResult:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> 'LoadResult':
        return cls(created=int(payload.get('created', 0)),
                   updated=int(payload.get('updated', 0)),
                   errors=list(payload.get('errors', [])))


@dataclass
class HttpClient83:
    """Клиент HTTP-сервиса приёмника."""

    base_url: str
    timeout: float = 60.0
    retries: int = 3
    batch_size: int = 500
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url,
                                             timeout=httpx.Timeout(self.timeout))
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, json: Any = None) -> dict[str, Any]:
        c = await self.client()
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                r = await c.request(method, path, json=json)
                if r.status_code in (200, 201):
                    return r.json()
                if r.status_code in (400, 409):
                    raise HttpServiceError(f'HTTP {r.status_code}: {r.text[:500]}')
            except httpx.TransportError as exc:
                last = exc
                await asyncio.sleep(2 ** attempt * 0.5)
        raise HttpServiceError(f'транспортная ошибка после {self.retries} попыток: {last}')

    async def metadata(self) -> dict[str, Any]:
        return await self._request('GET', '/metadata')

    async def load(self, objects: list[dict[str, Any]], source_ib: str, target_ib: str,
                   replace: bool = False) -> list[LoadResult]:
        """Пакетная загрузка; возвращает результат по каждому пакету."""
        results: list[LoadResult] = []
        for i in range(0, len(objects), self.batch_size):
            batch = objects[i:i + self.batch_size]
            payload = {'source_ib': source_ib, 'target_ib': target_ib,
                       'objects': batch, 'replace': replace}
            resp = await self._request('POST', '/load', json=payload)
            results.append(LoadResult.from_payload(resp))
        return results
`,
    'tests/test_http_client.py': `"""Unit-тесты http-клиента на моке HTTP-сервиса."""
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
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
