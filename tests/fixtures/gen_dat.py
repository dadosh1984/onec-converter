"""Генератор синтетического 1Cv77.dat (текстовый формат ИБ 1С 7.7, CP866).

Используется в unit-тестах: v77_reader должен разбирать файл, сгенерированный
этой функцией, и восстанавливать исходную структуру (round-trip).
"""

from __future__ import annotations

from typing import Any


def quote(value: Any) -> str:
    """Кавычки для строкового значения: удвоение кавычек внутри."""
    return '"' + str(value).replace('"', '""') + '"'


def fmt_value(value: Any) -> str:
    """Форматирование значения в терминал формата:
    строка -> "…", int/float -> число, None -> "" (пустая строка)."""
    if value is None:
        return '""'
    if isinstance(value, str):
        return quote(value)
    return str(value)


def fmt_record(record: list[Any]) -> str:
    return '{' + ','.join(fmt_value(v) for v in record) + '}'


def make_dat(
    unique_ids: dict[int, int] | None = None,
    constants: list[tuple[int, list[Any]]] | None = None,
    references: dict[int, list[list[Any]]] | None = None,
) -> bytes:
    """Собрать текст 1Cv77.dat и вернуть байты в CP866."""
    unique_ids = unique_ids or {1: 0}
    constants = constants or []
    references = references or {}

    parts: list[str] = []
    parts.append('{' + quote('7.70') + ',' + quote('') + ',')

    # System table — минимальный стенд (реальное содержимое не зафиксировано)
    parts.append('{' + quote('System table') + ',{0,0,' + quote('fixture') + '}},')

    inner = ','.join('{%d,%s}' % (tid, quote(f'{cnt}|')) for tid, cnt in sorted(unique_ids.items()))  # noqa: UP031
    parts.append('{' + quote('Unique IDs') + ',' + inner + '},')

    inner = ','.join('{%d,{%s}}' % (cid, ','.join(fmt_value(v) for v in vals))  # noqa: UP031
                     for cid, vals in constants)
    parts.append('{' + quote('Constants') + ',' + inner + '},')

    inner = ','.join('{%d,%s}' % (tid, ','.join(fmt_record(r) for r in recs))  # noqa: UP031
                     for tid, recs in references.items())
    parts.append('{' + quote('References') + ',' + inner + '},')

    parts.append('{' + quote('Template Operations') + ',{}},')
    parts.append('{' + quote('Correct Entries') + ',{}}')
    parts.append('}')
    return ''.join(parts).encode('cp866', errors='replace')
