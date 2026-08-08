// GREEN: потоковая обработка больших таблиц (итераторы, лимиты памяти)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption() {
  const files: Record<string, string> = {
    'src/onec_converter/streaming.py': `"""Потоковая обработка больших таблиц: итераторы, лимиты памяти.

Большие регистры/документы не должны целиком помещаться в память.
extract/transform/load работают с итераторами и пакетами фиксированного размера.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Callable, TypeVar

T = TypeVar('T')


def batch_iter(items: Iterable[T], size: int = 500) -> Iterator[list[T]]:
    """Разбиение итератора на пакеты фиксированного размера."""
    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


class Counted:
    """Считающий итератор: ограничение и подсчёт элементов."""

    def __init__(self, items: Iterable[T], limit: int | None = None):
        self._it = iter(items)
        self._limit = limit
        self.count = 0

    def __iter__(self) -> 'Counted':
        return self

    def __next__(self) -> T:
        if self._limit is not None and self.count >= self._limit:
            raise StopIteration
        item = next(self._it)
        self.count += 1
        return item


def map_limited(items: Iterable[T], func: Callable[[T], Any],
                limit: int | None = None) -> Iterator[Any]:
    """Функциональное отображение с ограничением и подсчётом (для extract/transform)."""
    c = Counted(items, limit)
    for item in c:
        yield func(item)
`,
    'tests/test_streaming.py': `"""Unit-тесты потоковой обработки."""
from onec_converter.streaming import batch_iter, Counted, map_limited


def test_batch_iter():
    assert list(batch_iter(range(5), 2)) == [[0, 1], [2, 3], [4]]


def test_counted_limit():
    c = Counted(range(1000), limit=3)
    assert list(c) == [0, 1, 2]
    assert c.count == 3


def test_map_limited():
    out = list(map_limited(range(10), lambda x: x * 2, limit=4))
    assert out == [0, 2, 4, 6]
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
