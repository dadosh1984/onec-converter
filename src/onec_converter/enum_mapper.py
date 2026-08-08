"""Авто-маппинг перечислений по именам (Фаза 35).

1С хранит значения перечислений как индексы, но правила TOON и промежуточный
JSON оперируют именами. EnumMapper строит соответствие значений между двумя
перечислениями по нормализованному имени (регистр/пробелы), позволяя
переносить регистр-поля даже если набор значений в приёмнике отличается или
порядок переставлен. Код авторский.
"""
from __future__ import annotations

import re
from collections.abc import Iterable


def normalize_enum_name(name: str) -> str:
    """Нормализация имени значения перечисления: регистр-фри, без лишних
    пробелов и разделителей. 'Статус заказа' == 'СТАТУС_ЗАКАЗА'."""
    s = name.strip().lower()
    s = re.sub(r'[\s_\-]+', ' ', s)
    return s.strip()


def build_enum_map(source_names: Iterable[str],
                   target_names: Iterable[str]) -> dict[str, str]:
    """Соответствие {нормализованное имя: целевое имя} для именования.

    Если в приёмнике нет совпадения по имени, значение не отображается
    (не заносится в результат — transform оставляет исходное имя).
    """
    tgt_by_norm: dict[str, str] = {}
    for n in target_names:
        tgt_by_norm.setdefault(normalize_enum_name(n), n)
    out: dict[str, str] = {}
    for n in source_names:
        key = normalize_enum_name(n)
        if key in tgt_by_norm:
            out[key] = tgt_by_norm[key]
    return out


def map_enum_value(value: object, enum_map: dict[str, str],
                   target_names: Iterable[str]) -> object:
    """Сопоставить значение перечисления источнику значением приёмника.

    value — имя значения (str) или индекс (int). При int — возвращается
    имя в позиции value из target_names (если целевое перечисление совпадает
    по порядку) иначе исходное значение. При str — возвращается целевое
    имя по enum_map либо нормализованное исходное.
    """
    if isinstance(value, int):
        names = list(target_names)
        if 0 <= value < len(names):
            return names[value]
        return value
    if isinstance(value, str):
        if value in enum_map:
            return enum_map[value]
        key = normalize_enum_name(value)
        if key in enum_map:
            return enum_map[key]
    return value
