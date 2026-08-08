"""Unit-тесты потоковой обработки."""
from onec_converter.streaming import Counted, batch_iter, map_limited


def test_batch_iter():
    assert list(batch_iter(range(5), 2)) == [[0, 1], [2, 3], [4]]


def test_counted_limit():
    c = Counted(range(1000), limit=3)
    assert list(c) == [0, 1, 2]
    assert c.count == 3


def test_map_limited():
    out = list(map_limited(range(10), lambda x: x * 2, limit=4))
    assert out == [0, 2, 4, 6]
