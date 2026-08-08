"""Чтение ИБ 8.3 через HTTP-сервис (единый механизм чтения/записи).

Когда источник — 8.3 и на нём установлено расширение (или HTTP-сервис чтения),
можно не открывать 1Cv8.1CD, а читать через HTTP. Контракт чтения:
  GET /metadata  — структура
  GET /objects?type=Справочник.Банки&limit=100&offset=0 — записи
Переиспользует HttpClient83; формат объектов — как в POST /load (обратная операция).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .http_client import HttpClient83


@dataclass
class HttpSource83:
    """Источник 8.3 через HTTP-сервис."""

    client: HttpClient83

    async def metadata(self) -> dict[str, Any]:
        return await self.client.metadata()

    async def objects(self, obj_type: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Чтение записей объекта (GET /objects)."""
        payload = await self.client._request('GET', '/objects', json={
            'type': obj_type, 'limit': limit, 'offset': offset})
        items: list[dict[str, Any]] = payload.get('objects', [])
        return items
