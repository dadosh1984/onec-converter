"""Асинхронный httpx-клиент HTTP-сервиса расширения 8.3 (/metadata, /load).

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
