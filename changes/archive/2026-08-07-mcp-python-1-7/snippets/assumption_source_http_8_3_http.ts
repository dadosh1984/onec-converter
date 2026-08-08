// GREEN: source_http — чтение ИБ 8.3 через HTTP-сервис (тот же контракт, что приёмник)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_source_http_8_3_http() {
  const files: Record<string, string> = {
    'src/onec_converter/source_http.py': `"""Чтение ИБ 8.3 через HTTP-сервис (единый механизм чтения/записи).

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
        return payload.get('objects', [])
`,
    'tests/test_source_http.py': `"""Тесты HTTP-источника."""
import pytest

from onec_converter.source_http import HttpSource83
from onec_converter.http_client import HttpClient83


@pytest.mark.asyncio
async def test_http_source_objects(monkeypatch):
    async def fake_request(self, method, path, json=None):
        return {'objects': [{'type': 'Справочник.Банки'}]}
    monkeypatch.setattr(HttpClient83, '_request', fake_request)
    src = HttpSource83(HttpClient83('http://x'))
    objs = await src.objects('Справочник.Банки')
    assert len(objs) == 1
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
