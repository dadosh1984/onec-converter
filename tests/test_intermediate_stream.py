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
    assert load_json_batch(p) == []
