"""Разрешение перечислений в xlsx-мосте: синоним -> _IDRREF приёмника.

`_Enum<N>` хранит только `_IDRREF` + `_ENUMORDER` (без имён). Имена/синонимы
значений лежат в CONFIG-скобкофайле объекта перечисления. Этот модуль
извлекает значения перечисления из CONFIG приёмника и строит индекс
{синоним (нормализованный) -> _IDRREF}. Связь со ссылкой — по позиции:
значение i в CONFIG соответствует строке i таблицы `_Enum<N>`.
"""
from __future__ import annotations

from typing import Any

from .enum_mapper import normalize_enum_name
from .source_8x_file import Database1CD, parse_bracket

ZERO16 = b'\x00' * 16

# layout значения-GUID в CONFIG -> 16 байт _IDRREF (проверено на реальной базе)
def guid_str_to_ref(guid: str) -> bytes:
    """'c9..-..5c-..3a-8251-7a57...' -> 16 байт ссылки приёмника.

    1С хранит ссылку в layout p3+p4+p2+p1+p0 (группы канонического GUID).
    """
    if not guid:
        return ZERO16
    try:
        parts = guid.split('-')
        if len(parts) != 5:
            return ZERO16
        return bytes.fromhex(parts[3] + parts[4] + parts[2] + parts[1] + parts[0])
    except ValueError:
        return ZERO16


def extract_enum_values(db: Database1CD, meta: dict[str, Any]) -> list[tuple[str, str]]:
    """Значения перечисления из CONFIG приёмника в порядке _ENUMORDER.

    meta — объект метаданных из read_metadata для полного имени
    'Перечисление.X' (несёт 'guid'). Возвращает [(name, synonym_ru)].
    Пустой список, если перечисление пустое или CONFIG не разобран.
    """
    guid = meta.get('guid', '')
    if not guid:
        return []
    raw = db.config_get(guid)
    if raw is None:
        return []
    try:
        tree = parse_bracket(raw.decode('utf-8-sig').lstrip('\ufeff'))
    except Exception:  # noqa: BLE001 — некорректный CONFIG не роняет импорт
        return []
    out: list[tuple[str, str, str]] = []

    # узел значений: [<guid>,<count>, <value1>, …, <valueN>]; находим глубоко
    def _walk_collect(node: Any) -> None:
        if (isinstance(node, list)
                and node
                and isinstance(node[0], str)
                and not isinstance(node[1], list)
                and str(node[1]).isdigit()
                and len(node) == int(str(node[1])) + 2
                and len(node) > 2
                and isinstance(node[2], list)):
            # коллекция значений: собрать value-объекты под ней
            for child in node[2:]:
                _collect_one(child)
            return
        if isinstance(node, list):
            for x in node:
                if isinstance(x, list):
                    _walk_collect(x)

    def _collect_one(node: Any) -> None:
        """Один value-объект {0,{0,{0,0,guid},name,{1,'ru',syn},syn},0}."""
        if (isinstance(node, list) and len(node) >= 2
                and isinstance(node[0], str) and node[0] == '0'):
            inner = node[1]
            if (isinstance(inner, list) and inner
                    and isinstance(inner[0], str) and inner[0] == '0'):
                spec = inner[1]
                if isinstance(spec, list) and len(spec) >= 3:
                    gid = spec[2]
                    name = inner[2] if len(inner) > 2 else ''
                    syn = ''
                    for el in inner[3:]:
                        if (isinstance(el, list) and len(el) >= 3
                                and el[0] == '1' and el[1] == 'ru'):
                            syn = el[2]
                            break
                    out.append((gid, name, syn))
                    return
        if isinstance(node, list):
            for x in node:
                if isinstance(x, list):
                    _collect_one(x)

    _walk_collect(tree)
    # убрать дубликаты по guid, сохранив порядок
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for gid, name, syn in out:
        if gid in seen:
            continue
        seen.add(gid)
        result.append((name, syn))
    return result


def in_enum_tables(table_name: str) -> bool:
    """Таблица `_Enum<N>` это перечисление ('_Enum' или '_ENUM')."""
    upper = table_name.upper()
    return upper.startswith('_ENUM') and upper[len('_ENUM'):].isdigit()


class EnumResolver:
    """Индекс синонимов перечисления отдельного объекта приёмника.

    values — при передаче используется как есть (для тестов без CONFIG);
    иначе извлекается из CONFIG приёмника через extract_enum_values.
    """

    def __init__(self, db: Database1CD, meta: dict[str, Any],
                 values: list[tuple[str, str]] | None = None) -> None:
        self._table = meta.get('table', '')
        self._by_syn: dict[str, bytes] = {}
        self._by_ref: dict[bytes, str] = {}
        enum_vals = values if values is not None else extract_enum_values(db, meta)
        self._build(db, enum_vals)

    def _build(self, db: Database1CD, enum_vals: list[tuple[str, str]]) -> None:
        # таблица перечисления: значение i в CONFIG == строка i (_ENUMORDER)
        t = db.tables.get(self._table) if self._table else None
        rows = self._table_rows(db, t) if t is not None else []
        for i, (name, syn) in enumerate(enum_vals):
            if i >= len(rows):
                break
            ref = rows[i]
            normalized = normalize_enum_name(syn or name)
            self._by_syn.setdefault(normalized, ref)
            self._by_ref.setdefault(ref, (syn or name))

    def _table_rows(self, db: Database1CD, t: Any) -> list[bytes]:
        idr = t.fields.get('_IDRREF')
        if idr is None:
            return []
        rows: list[bytes] = []
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            raw_id = row[idr.offset:idr.offset + 16]
            if raw_id == ZERO16:
                continue
            rows.append(raw_id)
        return rows

    def by_synonym(self, text: str) -> bytes:
        """Синоним -> _IDRREF приёмника; не найдено -> 16 нулей."""
        return self._by_syn.get(normalize_enum_name(text), ZERO16)

    def by_ref(self, ref: bytes) -> str:
        """_IDRREF -> синоним (для bridge_verify). Пустая строка если не найдено."""
        return self._by_ref.get(ref, '')
