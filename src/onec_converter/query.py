"""SQL-подобная консоль запросов к таблицам 1CD (Фаза 11, идея E1).

Безопасный мини-SQL без exec: только лексический разбор строк запроса.
Выполняется поверх `Database1CD.table_rows` — тот же коннектор, что у
`query_table` (C3), синтаксис WHERE совместим (расширение, не ломка).

Язык:
    SELECT:  '*' (по умолчанию) или список полей через запятую
    WHERE:   `f1=val; f2>10; f3 LIKE 'Текст%'`  — операторы =, !=, <, >, <=, >=, LIKE
    ORDER BY: `поле ASC|DESC`
    LIMIT:   целое число (по умолчанию 100)

REF-поля (тип `R`) отдаются как `{"guid": ..., "name": ...}` — имя через кеш
ссылок парсера (`ref_name`). Нулевая ссылка — `None`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .source_8x_file import Database1CD, FieldDef, bin_to_guid, decode_field

_OPS = ('>=', '<=', '!=', '=', '>', '<')
_LIKE_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s+LIKE\s+(.+?)\s*$', re.IGNORECASE)
_ORDER_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*(ASC|DESC)?\s*$', re.IGNORECASE)


class QueryError(ValueError):
    """Ошибка разбора или выполнения запроса."""


@dataclass(frozen=True)
class QueryCondition:
    field: str
    op: str  # '=' | '!=' | '<' | '>' | '<=' | '>=' | 'like'
    value: str


def parse_where(where: str) -> list[QueryCondition]:
    """Разбор WHERE: `f=1; g>2; name LIKE 'A%'` — список условий."""
    conds: list[QueryCondition] = []
    for part in (p for p in where.split(';') if p.strip()):
        for op in _OPS:
            if op in part:
                fname, _, raw = part.partition(op)
                conds.append(QueryCondition(fname.strip(), op, raw.strip()))
                break
        else:
            m = _LIKE_RE.match(part)
            if not m:
                raise QueryError(f'не разобрано условие WHERE: {part!r}')
            conds.append(QueryCondition(m.group(1), 'like', m.group(2)))
    return conds


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _match_like(value: Any, pattern: str) -> bool:
    """LIKE: поддерживает `%` в начале/конце/середине (регистронезависимо)."""
    s = str(value).lower()
    p = pattern.lower().strip("'\"")
    if p.startswith('%') and p.endswith('%'):
        return p[1:-1] in s
    if p.startswith('%'):
        return s.endswith(p[1:])
    if p.endswith('%'):
        return s.startswith(p[:-1])
    return s == p


def decode_value(db: Database1CD, table_name: str, fdef: FieldDef,
                 raw: bytes) -> Any:
    """Декодирование значения поля; REF (тип `R`) — {guid, name}."""
    if fdef.type == 'R':
        if len(raw) == 16 and raw != b'\x00' * 16:
            return {'guid': bin_to_guid(raw), 'name': db.ref_name(table_name, raw)}
        return None
    return decode_field(fdef, raw)


def query_table_sql(db: Database1CD, table: str, select: str = '*',
                    where: str = '', order_by: str = '', limit: int = 100) \
        -> list[dict[str, Any]]:
    """SQL-подобная выборка записей таблицы.

    SELECT — `*` или список полей; WHERE — условия через `;`; ORDER BY —
    `поле ASC|DESC` (применяется к отобранным `limit` строкам); LIMIT — число.
    Ошибки: QueryError (нет таблицы/поля, не разобрался синтаксис).
    """
    if limit < 1:
        raise QueryError(f'limit должен быть >= 1: {limit}')
    if table not in db.tables:
        raise QueryError(f'таблица не найдена: {table}')
    t = db.tables[table]

    sel: list[str] | None = None
    if select and select.strip() != '*':
        sel = [f.strip() for f in select.split(',') if f.strip()]
        missing = [f for f in sel if f not in t.fields]
        if missing:
            raise QueryError(f'нет полей: {", ".join(missing)}')

    conds = parse_where(where)
    for c in conds:
        if c.field not in t.fields:
            raise QueryError(f'нет поля: {c.field}')

    order_field: str | None = None
    order_desc = False
    if order_by and order_by.strip():
        m = _ORDER_RE.match(order_by)
        if not m:
            raise QueryError(f'не разобрано ORDER BY: {order_by!r}')
        order_field = m.group(1)
        order_desc = (m.group(2) or 'ASC').upper() == 'DESC'
        if order_field not in t.fields:
            raise QueryError(f'нет поля для ORDER BY: {order_field}')

    rows: list[dict[str, Any]] = []
    for row in db.table_rows(t):
        rec = {fn: decode_value(db, table, fd,
                                row[fd.offset:fd.offset + fd.size])
               for fn, fd in t.fields.items()}
        ok = True
        for c in conds:
            val = rec[c.field]
            if c.op == 'like':
                ok = _match_like(val, c.value)
            else:
                nv, ne = _num(val), _num(c.value)
                if nv is not None and ne is not None:
                    a: Any = nv
                    b: Any = ne
                else:
                    a = str(val)
                    b = c.value
                if c.op == '=':
                    ok = a == b
                elif c.op == '!=':
                    ok = a != b
                elif c.op == '>':
                    ok = a > b
                elif c.op == '<':
                    ok = a < b
                elif c.op == '>=':
                    ok = a >= b
                else:  # '<='
                    ok = a <= b
            if not ok:
                break
        if ok:
            rows.append(rec)
            if len(rows) >= limit:
                break

    if order_field is not None:
        def _sort_key(r: dict[str, Any]) -> tuple[float | str, str]:
            v = r.get(order_field)
            n = _num(v)
            if n is not None:
                return (n, str(v))
            return (str(v or ''), '')

        rows.sort(key=_sort_key, reverse=order_desc)

    if sel is not None:
        rows = [{f: r[f] for f in sel} for r in rows]
    return rows
