"""Unit-тесты кеша."""
from pathlib import Path

from onec_converter.cache import Cache, file_key


def test_put_get_roundtrip(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    key = 'abc123'
    c.put(key, 'meta.json', b'{}')
    assert c.has(key, 'meta.json')
    p = c.get(key, 'meta.json')
    assert p is not None and p.read_bytes() == b'{}'


def test_file_key_stability(tmp_path: Path):
    f = tmp_path / 'base.dat'
    f.write_bytes(b'data')
    k1 = file_key(f)
    k2 = file_key(f)
    assert k1 == k2 and len(k1) == 16


def test_file_key_invalidates_on_change(tmp_path: Path):
    f = tmp_path / 'base.dat'
    f.write_bytes(b'data')
    k1 = file_key(f)
    f.write_bytes(b'data2')
    k2 = file_key(f)
    assert k1 != k2


def test_clear(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    c.put('k', 'a', b'1')
    c.clear()
    assert not c.has('k', 'a')
