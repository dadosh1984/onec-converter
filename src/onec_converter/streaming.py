"""Потоковая обработка больших таблиц: итераторы, лимиты памяти.

Большие регистры/документы не должны целиком помещаться в память.
extract/transform/load работают с итераторами и пакетами фиксированного размера.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, Generic, TypeVar

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


class Counted(Generic[T], Iterator[T]):  # noqa: PYI059
    """Считающий итератор: ограничение и подсчёт элементов."""

    def __init__(self, items: Iterable[T], limit: int | None = None):
        self._it: Iterator[T] = iter(items)
        self._limit = limit
        self.count = 0

    def __iter__(self) -> Iterator[T]:  # noqa: PYI034
        return self

    def __next__(self) -> T:
        if self._limit is not None and self.count >= self._limit:
            raise StopIteration
        item: T = next(self._it)
        self.count += 1
        return item


def map_limited(items: Iterable[T], func: Callable[[T], Any],
                limit: int | None = None) -> Iterator[Any]:
    """Функциональное отображение с ограничением и подсчётом (для extract/transform)."""
    c = Counted(items, limit)
    for item in c:
        yield func(item)
