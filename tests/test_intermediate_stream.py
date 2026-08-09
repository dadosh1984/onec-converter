"""Фаза 20: потоковая сериализация intermediate (без OOM)."""
from __future__ import annotations

from pathlib import Path

from onec_converter.intermediate import (
    load_json_batch,
    load_json_stream,
    save_json_batch,
    save_json_stream,
)


def test_stream_roundtrip_equal_to_batch(tmp_path: Path):
    objs = [{'type': 'Справочник.X', 'key': [f'{i}'], 'attributes': {'Код': f'{i}'}}
            for i in range(20)]
    p1 = tmp_path / 'batch.json'
    p2 = tmp_path / 'stream.json'
    save_json_batch(objs, p1)
    save_json_stream(iter(objs), p2)
    # content valid JSON, loads to same objects
    assert load_json_batch(p1) == load_json_batch(p2)
    streamed = list(load_json_stream(p2))
    assert streamed == objs


def test_stream_rejects_no_first_objects(tmp_path: Path):
    p = tmp_path / 'empty.json'
    save_json_stream(iter([]), p)
    assert list(load_json_stream(p)) == []


def test_stream_encodes_bytes_fields(tmp_path: Path):
    """BLOB-поля 1С (bytes) должны сериализоваться без исключения (base64)."""
    objs = [{'type': 'Таблица._X', 'key': ['0'],
             'attributes': {'Картинка': b'\x89PNG\x00', 'BLOB': bytes(range(256))}}]
    p = tmp_path / 'blob.json'
    save_json_batch(objs, p)
    save_json_stream(iter(objs), tmp_path / 'blob_stream.json')
    loaded = load_json_batch(p)
    import base64
    assert loaded[0]['attributes']['Картинка'] == base64.b64encode(b'\x89PNG\x00').decode('ascii')
    assert next(load_json_stream(tmp_path / 'blob_stream.json')) == loaded[0]
