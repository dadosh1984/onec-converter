"""Асинхронный httpx-клиент HTTP-сервиса расширения 8.3 (/metadata, /load).

Пакетная загрузка (до batch_size объектов на запрос), retry с экспоненциальной
задержкой, таймауты, декодирование ответов, идемпотентная повторная отправка.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, cast

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
    def from_payload(cls, payload: dict[str, Any]) -> LoadResult:
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
    transport: httpx.AsyncBaseTransport | None = None
    api_key: str | None = None
    # OAuth2 client-credentials (Фаза 22): если задан token_url, клиент
    # получает Bearer-токен и шлёт его в Authorization; иначе — X-API-Key.
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    # Локальный mint-token (Фаза 33): shared secret для выпуска HS256 JWT
    # на месте, без OAuth2-сервера (см. jwt_auth.mint_jwt). Используется,
    # когда задан secret, но token_url не задан.
    secret: str | None = None
    issuer: str = 'onec-converter'
    max_token_attempts: int = 5  # лимит запросов токена за сессию (Фаза 47)
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _token: str | None = field(default=None, init=False, repr=False)
    _token_exp: float = field(default=0.0, init=False, repr=False)
    _token_attempts: int = field(default=0, init=False, repr=False)

    async def _ensure_token(self) -> None:
        """Обеспечить действующий Bearer-токен.

        token_url — OAuth2 client-credentials (внешний сервер); secret без
        token_url — локальный mint-token (HS256 JWT на shared secret, без
        инфраструктуры). Без обоих — режим X-API-Key.
        """
        if not self.token_url and not self.secret:
            return
        if self._token and time.time() < self._token_exp:
            return
        if self.secret and not self.token_url:
            from .jwt_auth import mint_jwt
            ttl = 3600
            self._token = mint_jwt(self.secret, self.issuer, ttl, extra={
                'sub': 'onec-loader'})
            self._token_exp = time.time() + ttl * 0.9
            return
        assert self.token_url is not None  # ветка OAuth2 (token_url задан)
        # защита от зацикливания при постоянном 401/сбое сервера (Фаза 47):
        # лимит попыток запроса токена за сессию клиента
        if self._token_attempts >= self.max_token_attempts:
            raise HttpServiceError(
                f'token: превышен лимит попыток '
                f'({self.max_token_attempts}) за сессию — сервер токенов '
                f'недоступен или отвечает ошибками')
        self._token_attempts += 1
        payload = {'grant_type': 'client_credentials',
                   'client_id': self.client_id or '',
                   'client_secret': self.client_secret or ''}
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout),
                                     transport=self.transport) as c:
            r = await c.post(self.token_url, data=payload)
        if r.status_code != 200:
            raise HttpServiceError(
                f'token: HTTP {r.status_code}: {r.text[:200]}')
        data = r.json()
        token = data.get('access_token')
        if not isinstance(token, str) or not token:
            raise HttpServiceError('token: нет access_token в ответе')
        expires_in = int(data.get('expires_in', 3600))
        self._token = token
        self._token_exp = time.time() + expires_in * 0.9

    async def _auth_headers(self) -> dict[str, str]:
        await self._ensure_token()
        if self._token:
            return {'Authorization': f'Bearer {self._token}'}
        return {}

    async def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {}
            if self.api_key and not self.token_url:
                headers['X-API-Key'] = self.api_key
            self._client = httpx.AsyncClient(base_url=self.base_url,
                                             timeout=httpx.Timeout(self.timeout),
                                             transport=self.transport,
                                             headers=headers)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, json: Any = None) -> dict[str, Any]:
        c = await self.client()
        last_error: str | None = None
        for attempt in range(self.retries):
            try:
                headers = await self._auth_headers()
                r = await c.request(method, path, json=json, headers=headers)
                if r.status_code in (200, 201):
                    return cast(dict[str, Any], r.json())
                if (r.status_code == 401 and self.token_url and self._token
                        and attempt < self.retries - 1):
                    # токен отвергнут — принудительно обновим и повторим
                    self._token = None
                    self._token_exp = 0.0
                    headers = await self._auth_headers()
                    r = await c.request(method, path, json=json, headers=headers)
                    if r.status_code in (200, 201):
                        return cast(dict[str, Any], r.json())
                if 400 <= r.status_code < 500:
                    # клиентская ошибка: ретраить бесполезно, вернуться с подробностью
                    raise HttpServiceError(
                        f'HTTP {r.status_code}: {r.text[:500]}')
                # 5xx/другие — ретрай с экспоненциальной задержкой
                last_error = f'HTTP {r.status_code}: {r.text[:200]}'
            except httpx.TransportError as exc:
                last_error = f'transport: {exc!r}'
                if attempt + 1 < self.retries:
                    await asyncio.sleep(2 ** attempt * 0.5)
                continue
            if attempt + 1 < self.retries:
                await asyncio.sleep(2 ** attempt * 0.5)
        raise HttpServiceError(
            f'после {self.retries} попыток: {last_error or "нет ответа"}')

    async def metadata(self) -> dict[str, Any]:
        return await self._request('GET', '/metadata')

    async def load(self, objects: list[dict[str, Any]], source_ib: str, target_ib: str,
                   replace: bool = False) -> list[LoadResult]:
        """Пакетная загрузка; возвращает результат по каждому пакету.

        Идемпотентность записи достигается через `replace=true` (пишем по
        ключу, повторные пакеты при сетевом ретрае обновляют, а не дублируют,
        U29). HTTP-заголовок с ключом пакета не требуется.
        """
        results: list[LoadResult] = []
        for i in range(0, len(objects), self.batch_size):
            batch = objects[i:i + self.batch_size]
            payload = {'source_ib': source_ib, 'target_ib': target_ib,
                       'objects': batch, 'replace': replace}
            resp = await self._request('POST', '/load', json=payload)
            results.append(LoadResult.from_payload(resp))
        return results
