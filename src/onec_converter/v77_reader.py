"""Парсер текстового файла данных ИБ 1С 7.7 (1Cv77.dat).

Формат (подтверждён на реальной базе, см. docs/format-77.md):
  {"7.70","",{"System table",...},{"Unique IDs",{<tid>,"<cnt>|",...}},
   {"Constants",{<id>,{...}}},{"References",{<tid>,{записи}}},...,
   {"Template Operations",{}},{"Correct Entries",{}}}
Значения: строки "…" (CP866, удвоение кавычек), числа с точкой, даты YYYYMMDD,
ссылки "NNN|" (внутренний числовой ID записи).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any


class DatSyntaxError(ValueError):
    """Ошибка синтаксиса текста 1Cv77.dat."""


def _is_bare_start(ch: str) -> bool:
    return ch not in '{},"' and not ch.isspace()


def parse_dat(text: str) -> list[Any]:
    """Рекурсивный парсер текста 1Cv77.dat -> вложенные списки/скаляры.

    Строки в кавычках -> str; числа (int/float) -> int/float; прочее -> str.
    """
    n = len(text)
    pos = 0

    def skip_ws() -> None:
        nonlocal pos
        while pos < n and text[pos].isspace():
            pos += 1

    def parse_string() -> str:
        nonlocal pos
        assert text[pos] == '"'
        pos += 1
        out: list[str] = []
        while pos < n:
            ch = text[pos]
            if ch == '"':
                if pos + 1 < n and text[pos + 1] == '"':
                    out.append('"')
                    pos += 2
                    continue
                pos += 1
                return ''.join(out)
            out.append(ch)
            pos += 1
        raise DatSyntaxError('не закрыта строка')

    def parse_bare() -> Any:
        nonlocal pos
        start = pos
        while pos < n and text[pos] not in '{},':
            pos += 1
        token = text[start:pos].strip()
        if token == '':
            raise DatSyntaxError('пустой токен')
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError:
            return token

    def parse_list() -> list[Any]:
        nonlocal pos
        assert text[pos] == '{'
        pos += 1
        lst: list[Any] = []
        while True:
            skip_ws()
            if pos >= n:
                raise DatSyntaxError('неожиданный конец файла')
            ch = text[pos]
            if ch == '}':
                pos += 1
                return lst
            if ch == '{':
                lst.append(parse_list())
            elif ch == '"':
                lst.append(parse_string())
            elif _is_bare_start(ch):
                lst.append(parse_bare())
            else:
                raise DatSyntaxError(f'неожиданный символ {ch!r} на позиции {pos}')
            skip_ws()
            if pos < n and text[pos] == ',':
                pos += 1

    skip_ws()
    root = parse_list()
    skip_ws()
    return root


def iter_sections(root: list[Any]) -> Iterator[tuple[str, list[Any]]]:
    """Итерация по секциям верхнего уровня: (имя, payload-список)."""
    for item in root:
        if isinstance(item, list) and item and isinstance(item[0], str):
            yield item[0], item[1:]


def _section_name(text: str) -> str:
    """Имя секции из её текста {'Имя', ...} — без полного парсинга."""
    m = re.match(r'^\s*\{\s*"((?:[^"]|"")*)"', text)
    return m.group(1).replace('""', '"') if m else ''


def iter_sections_text(path: str | Path, encoding: str = 'cp866')\
        -> Iterator[tuple[str, str]]:
    """Потоковое чтение top-level секций 1Cv77.dat: (имя, текст секции).

    Читает файл через mmap и сканирует байты (строки в кавычках с удвоением,
    фигурные скобки), извлекая каждую секцию на глубине 1 целиком — в
    памяти одна секция, а не весь файл . Реальный 1Cv77.dat
    — один длинный текст; построчное чтение не помогает.
    """
    import mmap

    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            n = len(mm)
            i = 0
            depth = 0
            sec_start: int | None = None
            while i < n and mm[i] != ord('{'):
                i += 1
            if i >= n:
                return
            i += 1
            depth = 1
            while i < n:
                c = mm[i]
                if c == ord('"'):  # строка: пропустить (с удвоенными кавычками)
                    i += 1
                    while i < n:
                        if mm[i] == ord('"'):
                            if i + 1 < n and mm[i + 1] == ord('"'):
                                i += 2
                                continue
                            break
                        i += 1
                    i += 1
                    continue
                if c == ord('{'):
                    if depth == 1:
                        sec_start = i
                    depth += 1
                    i += 1
                    continue
                if c == ord('}'):
                    depth -= 1
                    if depth == 1 and sec_start is not None:
                        text = mm[sec_start:i + 1].decode(encoding,
                                                          errors='replace')
                        name = _section_name(text)
                        if name:
                            yield name, text
                        sec_start = None
                    if depth == 0:
                        return
                    i += 1
                    continue
                i += 1
        finally:
            mm.close()


class Section:
    """Секция файла данных: имя + payload."""

    __slots__ = ('name', 'payload')

    def __init__(self, name: str, payload: list[Any]):
        self.name = name
        self.payload = payload


class V77Reader:
    """Чтение 1Cv77.dat: секции, Unique IDs, Constants, References.

    Секции читаются потоково (iter_sections_text: в память
    попадает одна секция за раз, а не весь файл.
    """

    def __init__(self, path: str | Path, encoding: str = 'cp866'):
        self.path = Path(path)
        self.encoding = encoding
        self._sections: dict[str, Section] = {}
        for name, text in iter_sections_text(path, encoding):
            parsed = parse_dat(text)
            self._sections[name] = Section(name, parsed[1:])

    @classmethod
    def from_bytes(cls, data: bytes, encoding: str = 'cp866') -> V77Reader:
        """Чтение из байтов (для тестов на фикстурах)."""
        obj = cls.__new__(cls)
        obj.path = Path('<bytes>')
        obj.encoding = encoding
        parsed = parse_dat(data.decode(encoding, errors='replace'))
        obj._sections = {}
        for name, payload in iter_sections(parsed):
            obj._sections[name] = Section(name, payload)
        return obj

    def sections(self) -> list[str]:
        return list(self._sections)

    def unique_ids(self) -> dict[int, int]:
        """id_таблицы -> счётчик записей (из секции Unique IDs)."""
        sec = self._sections.get('Unique IDs')
        out: dict[int, int] = {}
        if sec is None:
            return out
        for entry in sec.payload:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tid = entry[0]
            cnt = str(entry[1])
            m = re.match(r'^(\d+)\|', cnt)
            out[int(tid)] = int(m.group(1)) if m else 0
        return out

    def constants(self) -> list[tuple[int, list[Any]]]:
        """Список (id константы, список значений)."""
        sec = self._sections.get('Constants')
        out: list[tuple[int, list[Any]]] = []
        if sec is None:
            return out
        for entry in sec.payload:
            if isinstance(entry, list) and len(entry) >= 2 and isinstance(entry[1], list):
                out.append((int(entry[0]), entry[1]))
        return out

    def references(self) -> dict[int, list[list[Any]]]:
        """id_таблицы справочника -> записи (каждая запись — список значений)."""
        sec = self._sections.get('References')
        out: dict[int, list[list[Any]]] = {}
        if sec is None:
            return out
        for entry in sec.payload:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tid = int(entry[0])
            recs: list[list[Any]] = []
            for r in entry[1:]:
                if isinstance(r, list):
                    recs.append(r)
            out[tid] = recs
        return out

    def record_count(self, table_id: int) -> int:
        """Число записей таблицы по счётчику Unique IDs."""
        return self.unique_ids().get(table_id, 0)
