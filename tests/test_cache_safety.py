"""Фаза 18: безопасность кеша (path traversal) и статистика + Strict Mode."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.cache import Cache
from onec_converter.strict import validate_object, validate_value


# ---- Cache safety ----
def test_cache_rejects_path_traversal(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    for bad in ('../evil', 'a/../b', '..', 'x/y'):
        with pytest.raises(ValueError):
            c.put(bad, 'meta.json', b'x')
        with pytest.raises(ValueError):
            c.put('good', bad, b'x')
    # внутри root ничего postороннего не создано
    assert not (tmp_path / 'cache' / '..' / '..' / 'evil').exists()


def test_cache_name_with_dot_ok(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    c.put('abc123', 'meta.json', b'{}')
    assert c.has('abc123', 'meta.json')


def test_cache_stats(tmp_path: Path):
    c = Cache(tmp_path / 'cache')
    c.put('k1', 'a', b'12345')
    c.put('k2', 'b', b'123')
    st = c.stats()
    assert st['files'] == 2 and st['bytes'] == 8


# ---- Strict Mode ----
class _FM:
    def __init__(self, name, ftype, length=0, precision=0):
        self.name = name; self.ftype = ftype; self.length = length; self.precision = precision


def test_strict_string_length():
    assert validate_value('NVC', 5, 0, 'слишкомдлиннэ')  # >5
    assert not validate_value('NVC', 10, 0, 'коротк')   # <=10


def test_strict_number_range():
    assert not validate_value('N', 4, 0, 12.5)     # <10^4
    assert validate_value('N', 1, 0, 100)          # >10^1


def test_strict_date():
    assert not validate_value('DT', 0, 0, '20240101120000')
    assert validate_value('DT', 0, 0, '20241301120000')  # месяц 13


def test_strict_ref():
    assert not validate_value('B', 0, 0, b'\x11' * 16)
    assert validate_value('B', 0, 0, b'\x11' * 8)       # не 16 байт


def test_strict_object_detects_bad():
    fm = [_FM('Код', 'NVC', 5), _FM('Вес', 'N', 1)]
    obj = {'type': 'Справочник.X', 'attributes': {'Код': 'len>5bad', 'Вес': 999}}
    rep = validate_object(obj, fm)
    assert not rep.ok and len(rep.errors) >= 2


def test_strict_ok():
    fm = [_FM('Код', 'NVC', 5)]
    rep = validate_object({'type': 'X', 'attributes': {'Код': 'ok'}}, fm)
    assert rep.ok
