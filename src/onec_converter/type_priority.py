"""TYPE_PRIORITY — детерминированный порядок типов при конвертации полей .

Источник: 1cdtools «TYPE_PRIORITY»; в нашем проекте — аналог `_DBNAME_PRIORITY`
() для полей. Когда поле источника имеет составной тип или типы
источника и приёмника не совпадают, нужен однозначный выбор целевого типа:
    string < number < date < bool < ref < unknown
Строка первична (наименования/коды важнее), число — следующее по важности
и т.д.
"""

from __future__ import annotations

from collections.abc import Iterable

# kind -> ранг (меньше = приоритетнее)
TYPE_RANK: dict[str, int] = {
    'string': 0,
    'number': 1,
    'date': 2,
    'bool': 3,
    'ref': 4,
    'unknown': 5,
}


def type_rank(kind: str) -> int:
    """Ранг типа: string(0) < number(1) < date(2) < bool(3) < ref(4) < unknown(5)."""
    return TYPE_RANK.get(kind, 5)


def resolve_type_priority(kinds: Iterable[str]) -> str:
    """Выбор целевого типа из набора по приоритету.

    Примеры:
        ['number', 'string']  -> 'number'
        ['date', 'number']    -> 'number'
        ['bool', 'ref']       -> 'bool'
        [] / ['unknown']      -> 'unknown'
    """
    best = 'unknown'
    best_rank = len(TYPE_RANK) + 1
    for kind in kinds:
        rank = type_rank(kind)
        if rank < best_rank:
            best_rank = rank
            best = kind
    return best
