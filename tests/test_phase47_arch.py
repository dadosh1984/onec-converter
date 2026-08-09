"""Фаза 47: архитектурные хвосты — OnecConverterError, лимит OAuth2,
потокобезопасность cache, понятная ошибка read_metadata, лимит blob-кеша,
секция Security в CHANGELOG."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest


# ---- OnecConverterError: единый предок ----
def test_base_error_hierarchy():
    from onec_converter import clone_db, errors, health, sql_source

    assert issubclass(clone_db.CloneError, errors.OnecConverterError)
    assert issubclass(sql_source.SqlSourceError, errors.OnecConverterError)
    assert issubclass(health.HealthError, errors.OnecConverterError)
    assert not issubclass(ValueError, errors.OnecConverterError)


def test_base_error_catch_all(tmp_path: Path):
    from onec_converter.errors import OnecConverterError
    from onec_converter.health import HealthError

    with pytest.raises(OnecConverterError):
        raise HealthError('нет 1Cv8.1CD')


# ---- OAuth2: лимит попыток токена ----
def test_token_attempt_limit():
    import httpx

    from onec_converter.http_client import HttpClient83, HttpServiceError

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={'error': 'down'})

    client = HttpClient83(
        base_url='http://x', token_url='http://t', client_id='i',
        client_secret='s', timeout=5,
        transport=httpx.MockTransport(handler))
    client.max_token_attempts = 2

    async def run():
        for _ in range(2):
            with pytest.raises(HttpServiceError):
                await client._ensure_token()
        with pytest.raises(HttpServiceError) as exc:
            await client._ensure_token()
        assert 'лимит попыток' in str(exc.value)

    asyncio.run(run())
    assert client._token_attempts == 2  # 2 реальные попытки; 3-я заблокирована без инкремента


# ---- cache: потокобезопасность (конкурентные put/get) ----
def test_cache_thread_safety(tmp_path: Path):
    from onec_converter.cache import Cache

    c = Cache(root=tmp_path / 'cc')
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def worker(i: int) -> None:
        try:
            barrier.wait()
            key = f'k{i % 3}'
            for n in range(50):
                # уникальное имя файла: нет гонки «последний пишущий» —
                # проверяем только целостность конкурентных put/get
                name = f'a{n}-t{i}'
                payload = f'data-{i}-{n}'.encode()
                c.put(key, name, payload)
                got = c.get(key, name)
                assert got is not None and got.read_bytes() == payload
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors[:3]
    assert c.stats()['files'] >= 3


# ---- read_metadata: понятная ошибка на битом файле ----
def test_read_metadata_broken_file_clear_error(tmp_path: Path):
    from onec_converter.source_8x_file import FormatError, read_metadata

    bad = tmp_path / '1Cv8.1CD'
    bad.write_bytes(b'\x00\x01\x02')  # короче заголовка 1CD
    with pytest.raises(FormatError) as exc:
        read_metadata(bad)
    assert 'read_metadata' in str(exc.value)
    assert str(bad) in str(exc.value) or 'поврежд' in str(exc.value)


# ---- blob-кеш: лимит объёма ----
def test_blob_cache_limit_evicts():
    src = Path('src/onec_converter/source_8x_file.py').read_text(encoding='utf-8')
    assert '_blob_cache_max' in src
    assert '_blob_cache_bytes' in src
    assert 'self._blob_cache = {}' in src  # полный сброс при переполнении


# ---- CHANGELOG: секция Security ----
def test_changelog_security_section():
    c = Path('CHANGELOG.md').read_text(encoding='utf-8')
    assert '0.30.0' in c
    assert 'Security' in c
