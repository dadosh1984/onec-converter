"""Собственный парсер файловой ИБ 1С 8.x (1Cv8.1CD) — полное чтение.

Формат подтверждён спайком на реальной базе `1C_8.1` (см. docs/format-8x.md,
раздел «Спайк 5.1»). Ключевые факты:

- заголовок `1CDBMSV8` + версия; страницы 8192 (8.2.14+) / 4096;
- root-объект БД (страница 2): сигнатура `1c fd`, fat_level 0/1, длина (uint64 @16),
  FAT-таблица номеров страниц с PAGE_HEADER_SIZE=24;
- данные root — цепочки blob-чанков по 256 байт ([nxt:uint32][size:int16] + payload);
  каталог таблиц — цепочка от чанка 1: [locale:32s][count:int32][offsets…],
  каждый offset — UTF-8 описание таблицы:
  `{"Name",0,{"Fields",{<поля>}},{"Indexes",…},{"Recordlock","0"},{"Files",d,b,i}}`;
  поле: `{"имя","тип",<null>,<длина>,<точность>,"CS/CI"}`;
- раскладка строки: RV — всегда offset 1; остальные поля последовательно
  (стартовый offset 17 при наличии RV, иначе 1); размер поля:
  B=len, L=1, N=len//2+1, NC=len*2, NVC=len*2+2, RV=16, NT=8, I=8, DT=7;
  null_exists добавляет 1 байт флага (0x00 = null, 0x01 = значение);
- NVC: [flag?][len:uint16][utf-16le len*2][паддинг пробелами];
- строки таблицы: read_object(data_page) → нарезка по row_length;
- blob: read_object(blob_page) → чанки 256 б от first_chunk*256;
- DBSCHEMA: поле SERIALIZEDDATA, строки [flag:1][off:uint32][size:uint32] → blob → UTF-8-SIG;
- PARAMS/DBNames: `{guid,"Reference",<num>}` — авторитетная привязка GUID ↔ таблица;
- CONFIG: FILENAME/CREATION/MODIFIED/ATTRIBUTES/BINARYDATA(off+size) → blob → zlib raw.
"""

from __future__ import annotations

import mmap
import re
import struct
import time
import zlib
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from .cache import Cache, file_key
from .model import ObjectType
from .timings import Timings

_METADATA_CACHE_INSTANCE: Cache | None = None

PAGE_HEADER = b'1CDBMSV8'
PAGE_HEADER_SIZE = 24
OBJ_SIG = b'\x1c\xfd'
BLOB_CHUNK = 256

_GUID_RE = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                      r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')

_TABLE_NAME_RE = re.compile(r'\{"([^"]+)"')
_FIELD_RE = re.compile(r'\{"([^"]+)","([^"]+)",(\d+),(\d+),(\d+),"([^"]+)"\}')
_FILES_RE = re.compile(r'\{"Files",(\d+),(\d+),(\d+)\}')
_DBNAME_RE = re.compile(r'\{(' + _GUID_RE.pattern + r'),"([^"]+)",(\d+)\}')


class FormatError(Exception):
    """Ошибка формата 1CD."""


# ---------------------------------------------------------------------------
# Структуры
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    build: int
    revision: int

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.build}.{self.revision}'


@dataclass
class FieldDef:
    name: str
    type: str            # B, RV, L, N, NC, NVC, NT, I, DT
    null_exists: bool
    length: int
    precision: int
    case_sensitive: bool
    offset: int
    size: int


@dataclass
class TableDef:
    name: str
    fields: dict[str, FieldDef] = field(default_factory=dict)
    row_length: int = 0
    data_page: int = 0
    blob_page: int = 0
    index_page: int = 0


def _field_size(ftype: str, length: int) -> int:
    return {
        'B': length, 'L': 1, 'N': length // 2 + 1, 'NC': length * 2,
        'NVC': length * 2 + 2, 'RV': 16, 'NT': 8, 'I': 8, 'DT': 7,
    }.get(ftype, 0)


# ---------------------------------------------------------------------------
# Декодирование значений
# ---------------------------------------------------------------------------


def decode_nvc(buf: bytes, null_exists: bool = False) -> str | None:
    """NVC: [null-флаг] [len:uint16] [utf-16le] — паддинг пробелами."""
    if null_exists:
        if buf[:1] == b'\x00':
            return None
        buf = buf[1:]
    n = struct.unpack('<H', buf[:2])[0]
    return buf[2:2 + n * 2].decode('utf-16-le')


def decode_nc(buf: bytes) -> str:
    """NC: фиксированная строка utf-16le, паддинг нулями/пробелами."""
    return buf.decode('utf-16-le').rstrip('\x00').rstrip(' ')


def decode_numeric(buf: bytes, length: int, precision: int) -> int | float:
    """N: BCD-подобное; первый ниббл 0 = минус."""
    hex_str = buf.hex()
    sign = '-' if hex_str[0] == '0' else ''
    digits = hex_str[1:length + 1]
    if precision:
        body = digits[:length - precision] + '.' + digits[length - precision:]
        return float(sign + body)
    return int(sign + digits)


def decode_datetime(buf: bytes) -> datetime | None:
    """DT: 7 байт YYYYMMDDHHMMSS; нули = None. Даты 1С без часового пояса.

    В 1С дата-заглушка может содержать невалидные компоненты
    (например 0100-00-00 00:00:00) — возвращаем None, а не exception.
    """
    if len(buf) < 7 or buf[:2] == b'\x00\x00':
        return None
    try:
        return datetime.strptime(buf[:7].hex(), '%Y%m%d%H%M%S')
    except ValueError:
        return None


def decode_field(fdef: FieldDef, buf: bytes) -> Any:
    """Декодирование одного поля по описанию."""
    if fdef.type == 'NVC':
        return decode_nvc(buf, fdef.null_exists)
    if fdef.type == 'NC':
        return decode_nc(buf)
    if fdef.type == 'N':
        return decode_numeric(buf, fdef.length, fdef.precision)
    if fdef.type == 'DT':
        return decode_datetime(buf)
    if fdef.type == 'L':
        return int(buf[0]) if buf else 0
    if fdef.type in ('RV', 'B'):
        return bin_to_guid(buf)
    return buf


def bin_to_guid(raw: bytes) -> str:
    """16 байт -> канонический GUID 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'."""
    if len(raw) != 16:
        return raw.hex()
    h = raw.hex()
    return f'{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'


# ---------------------------------------------------------------------------
# Скобкофайлы (bracket) — текстовый формат конфигурации
# ---------------------------------------------------------------------------


class _Tok(str):
    """Лист дерева; quoted=True — «строка», иначе голое значение."""

    quoted: bool

    def __new__(cls, value: str, quoted: bool = False) -> Self:
        obj = super().__new__(cls, value)
        obj.quoted = quoted
        return obj


def _merge_surrogates(s: str) -> str:
    """Склеить суррогатные пары UTF-16 (high+low) в один символ."""
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = ord(s[i])
        if 0xD800 <= c <= 0xDBFF and i + 1 < n and 0xDC00 <= ord(s[i + 1]) <= 0xDFFF:
            low = ord(s[i + 1])
            out.append(chr(((c - 0xD800) << 10) + (low - 0xDC00) + 0x10000))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def _parse_quoted(text: str, start: int) -> tuple[_Tok, int]:
    """Строка в кавычках.

    Возвращает (значение, новая позиция). Кавычка внутри строки всегда
    экранируется удвоением "" (и в 8.1, и в 8.3). Backslash — обычный
    символ, КРОМЕ суррогатов: \\d83c\\df10 = backslash + 4 hex
    в 0xD800-0xDFFF (UTF-16 суррогат; пара объединяется в один символ).
    Прочие backslash+4hex (например RTF \\deff0) остаются как есть.
    """
    pos = start + 1
    n = len(text)
    chunks: list[str] = []
    while pos < n:
        c = text[pos]
        if c == '"':
            if pos + 1 < n and text[pos + 1] == '"':
                chunks.append('"')
                pos += 2
                continue
            return _Tok(_merge_surrogates(''.join(chunks)), quoted=True), pos + 1
        if c == '\\' and pos + 5 <= n:
            try:
                cp = int(text[pos + 1:pos + 5], 16)
            except ValueError:
                cp = -1
            if 0xD800 <= cp <= 0xDFFF:
                if 0xD800 <= cp <= 0xDBFF and pos + 10 < n and text[pos + 5:pos + 6] == '\\':
                    # суррогатная пара \d83c\df10 -> один символ
                    try:
                        low = int(text[pos + 6:pos + 10], 16)
                    except ValueError:
                        low = -1
                    if 0xDC00 <= low <= 0xDFFF:
                        chunks.append(chr(((cp - 0xD800) << 10) + (low - 0xDC00) + 0x10000))
                        pos += 10
                        continue
                chunks.append(chr(cp))
                pos += 5
                continue
        chunks.append(c)
        pos += 1
    raise ValueError('незакрытая строка')


def _surrogate_cp(text: str, p: int) -> int:
    """Если на позиции p — backslash + 4 hex в 0xD800-0xDFFF, вернуть код, иначе -1."""
    if p + 5 > len(text) or text[p] != '\\':
        return -1
    try:
        cp = int(text[p + 1:p + 5], 16)
    except ValueError:
        return -1
    return cp if 0xD800 <= cp <= 0xDFFF else -1


def parse_bracket(text: str) -> list[Any]:
    """Разбор «скобкофайла» (UTF-8, допускается BOM).

    Формат: вложенные {a,b,{c,d},"строка"}; кавычка экранируется удвоением;
    значения вне кавычек могут содержать переносы строк (игнорируются).
    """
    if text.startswith('\ufeff'):
        text = text.removeprefix('\ufeff')
    pos = 0
    n = len(text)

    def skip_ws(p: int) -> int:
        while p < n and text[p] in ' \t\r\n':
            p += 1
        return p

    def parse_value(p: int) -> tuple[Any, int]:
        p = skip_ws(p)
        if p >= n:
            raise ValueError('неожиданный конец скобкофайла')
        ch = text[p]
        if ch == '{':
            return parse_list(p)
        if ch == '"':
            return _parse_quoted(text, p)
        cp = _surrogate_cp(text, p)
        if cp != -1:
            # голый суррогат 8.3 вне кавычек: "часть1"\d83c"\df10часть2"
            # = одна строка с символом (строка разорвана кавычками)
            return _Tok(chr(cp), quoted=True), p + 5
        chunks = []
        while p < n and text[p] not in ',}{':
            if text[p] not in ' \t\r\n':
                chunks.append(text[p])
            p += 1
        return _Tok(''.join(chunks), quoted=False), p

    def parse_list(p: int) -> tuple[list[Any], int]:
        assert text[p] == '{'
        p += 1
        items: list[Any] = []
        p = skip_ws(p)
        if p < n and text[p] == '}':
            return items, p + 1
        while True:
            value, p = parse_value(p)
            # 8.3: строка с суррогатом пишется разорванной: "часть1"\d83c"\df10часть2"
            # — соседние строковые литералы без запятой склеиваются
            while isinstance(value, _Tok) and value.quoted:
                p2 = skip_ws(p)
                if p2 >= n or (text[p2] != '\\' and text[p2] != '"'):
                    break
                cp = _surrogate_cp(text, p2)
                if text[p2] == '\\' and cp == -1:
                    break
                nxt, p2 = parse_value(p2)
                if not isinstance(nxt, _Tok) or not nxt.quoted:
                    break
                value = _Tok(_merge_surrogates(str(value) + str(nxt)), quoted=True)
                if p2 <= p:
                    break  # защита от зацикливания
                p = p2
            items.append(value)
            p = skip_ws(p)
            if p >= n:
                raise ValueError('неожиданный конец скобкофайла')
            if text[p] == ',':
                p += 1
                continue
            if text[p] == '}':
                return items, p + 1
            raise ValueError(f'неожиданный символ {text[p]!r} на позиции {p}')

    root, pos = parse_list(pos)
    return root


# ---------------------------------------------------------------------------
# База
# ---------------------------------------------------------------------------


class Database1CD:
    """Чтение файловой ИБ 8.x: каталог, строки, blob, DBSCHEMA, конфигурация.

    Режим только чтения; дескриптор живёт весь срок жизни объекта.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._f = open(self.path, 'rb')  # noqa: SIM115 — дескриптор живёт весь срок чтения
        self._mm: mmap.mmap | None = None
        try:
            self.version, self.total_pages, self.page_size = self._read_header()
            # mmap: чтение страниц = срез памяти, без seek+read на каждую страницу
            self._mm = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            self._f.close()
            raise
        self._tables: dict[str, TableDef] | None = None
        self._config_raw: list[tuple[TableDef, str, int, int]] | None = None
        self._config_index_: dict[str, tuple[TableDef, int, int]] | None = None
        self._config_inflated: dict[str, bytes] | None = None
        self._dbnames: dict[str, tuple[str, int]] | None = None
        self._locale = ''
        self._blob_cache: dict[int, bytes] = {}  # blob_page -> данные blob-таблицы
        self._blob_cache_bytes = 0
        self._blob_cache_max = 64 * 1024 * 1024  # лимит кеша blob ()
        self._root_data: bytes | None = None  # данные root-объекта (каталог)
        self._ref_table_cache: dict[str, dict[bytes, str]] = {}  # таблица -> idrref: имя
        self._ref_name_cache: dict[tuple[str, bytes], str | None] = {}
        self._stats_cache: dict[str, tuple[int, int]] = {}  # таблица -> (строки, байты)

    def table_stats(self, table_name: str) -> tuple[int, int]:
        """Размеры таблицы: (число строк, байт данных) — с кешем.

        Идея A2 (1C_PrometheusExporter): метрики таблиц для оценки объёма
        переноса. Лениво: данные таблицы читаются один раз и кешируются.
        Чтение точечное (mmap-срез страниц таблицы, а не
        полный проход по файлу.
        """
        if table_name not in self._stats_cache:
            t = self.tables[table_name]
            data = self.read_object(t.data_page) if t.data_page else b''
            rows = len(data) // t.row_length if t.row_length else 0
            self._stats_cache[table_name] = (rows, len(data))
        return self._stats_cache[table_name]

    def table_stats_all(self) -> dict[str, tuple[int, int]]:
        """Статистика всех таблиц одним проходом : общий кеш и mmap.

        Один цикл вместо N отдельных вызовов — каждый вызов table_stats
        ложится в общий кеш, повторные запросы не читают страницы.
        """
        for name in list(self.tables):
            self.table_stats(name)
        return dict(self._stats_cache)

    def ref_name(self, table_name: str, raw16: bytes) -> str | None:
        """Имя объекта таблицы по сырой ссылке (кеш ссылок GUID→наименование).

        Строит карту `_IDRREF -> имя` для таблицы один раз (лениво) и
        кеширует результат поиска. Нулевая ссылка -> None без обращения к БД.
        """
        if len(raw16) != 16 or raw16 == b'\x00' * 16:
            return None
        key = (table_name, raw16)
        if key in self._ref_name_cache:
            return self._ref_name_cache[key]
        table = self._ref_table_cache.get(table_name)
        if table is None:
            table = self._build_ref_index(table_name)
            self._ref_table_cache[table_name] = table
        name = table.get(raw16)
        self._ref_name_cache[key] = name
        return name

    def _build_ref_index(self, table_name: str) -> dict[bytes, str]:
        """idrref -> имя для таблицы (описание или первое строковое поле)."""
        t = self.tables[table_name]
        idr = t.fields.get('_IDRREF')
        desc = t.fields.get('_DESCRIPTION')
        name_f: FieldDef | None = desc
        if name_f is None:
            name_f = next((f for f in t.fields.values() if f.type in ('NVC', 'NC')), None)
        if idr is None or name_f is None:
            return {}
        out: dict[bytes, str] = {}
        for row in self.table_rows(t):
            if row[:1] == b'\x01':
                continue
            raw = row[idr.offset:idr.offset + idr.size]
            if len(raw) == 16 and raw != b'\x00' * 16:
                nm = decode_field(name_f, row[name_f.offset:name_f.offset + name_f.size])
                if isinstance(nm, str) and nm:
                    out[raw] = nm
        return out

    def close(self) -> None:
        if self._mm is not None:
            self._mm.close()
            self._mm = None
        self._f.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- заголовок ----
    def _read_header(self) -> tuple[Version, int, int]:
        head = self._f.read(24)
        if len(head) < 24:
            raise FormatError('файл короче заголовка 1CD')
        magic, v0, v1, v2, v3 = struct.unpack('<8s4b', head[:12])
        if magic != PAGE_HEADER:
            raise FormatError(f'не 1CD-файл: {magic!r}')
        total_pages = struct.unpack('<I', head[12:16])[0]
        page_size = struct.unpack('<I', head[20:24])[0]
        return Version(v0, v1, v2, v3), total_pages, page_size

    def read_page(self, num: int) -> bytes:
        """Страница из mmap (срез памяти — без системных вызовов на страницу)."""
        assert self._mm is not None
        start = num * self.page_size
        return self._mm[start:start + self.page_size]

    # ---- объекты (цепочки страниц) ----
    def read_object(self, header_page: int) -> bytes:
        """Содержимое объекта БД по странице-заголовку (fat_level 0/1)."""
        buf = self.read_page(header_page)
        if buf[:2] != OBJ_SIG:
            raise FormatError(f'не объект БД на странице {header_page}: {buf[:2].hex()}')
        fat_level = struct.unpack('<H', buf[2:4])[0]
        length = struct.unpack('<Q', buf[16:24])[0]
        n_entries = (self.page_size - PAGE_HEADER_SIZE) // 4
        fat = struct.unpack(f'<{n_entries}I', buf[PAGE_HEADER_SIZE:])
        if fat_level == 0:
            pages = [p for p in fat if p != 0]
            needed = (length + self.page_size - 1) // self.page_size
            pages = pages[:needed]
        elif fat_level == 1:
            pages = []
            for ip in fat:
                if ip == 0:
                    break
                ibuf = self.read_page(ip)
                for v in struct.unpack(f'<{self.page_size // 4}I', ibuf):
                    if v == 0:
                        break
                    pages.append(v)
        else:
            raise FormatError(f'неизвестный fat_level {fat_level}')
        data = b''.join(self.read_page(p) for p in pages)
        return data[:length]

    # ---- blob-цепочки root-объекта ----
    def _read_root_blob(self, start: int) -> bytes:
        if self._root_data is None:
            # root-объект читается один раз (каталог: 8033 таблиц -> 8033 blob-цепочек)
            self._root_data = self.read_object(2)
        data = self._root_data
        out: list[bytes] = []
        pos = start
        seen: set[int] = set()
        while pos and pos not in seen:
            seen.add(pos)
            block = data[pos * BLOB_CHUNK:(pos + 1) * BLOB_CHUNK]
            if len(block) < 6:
                break
            nxt, size = struct.unpack('<Ih', block[:6])
            out.append(block[6:6 + size])
            if nxt == 0:
                break
            pos = nxt
        return b''.join(out)

    # ---- каталог таблиц ----
    @property
    def locale(self) -> str:
        _ = self.tables  # каталог читается лениво; локаль из его заголовка
        return self._locale

    @property
    def tables(self) -> dict[str, TableDef]:
        if self._tables is None:
            head = self._read_root_blob(1)
            if len(head) < 36:
                raise FormatError('каталог таблиц пуст')
            self._locale = head[:32].decode('utf-8').rstrip('\x00')
            count = struct.unpack('<i', head[32:36])[0]
            offsets = struct.unpack(f'<{count}i', head[36:36 + 4 * count])
            self._tables = {}
            for off in offsets:
                desc = self._read_root_blob(off).decode('utf-8')
                td = self._parse_table_desc(desc)
                self._tables[td.name] = td
        return self._tables

    @staticmethod
    def _parse_table_desc(desc: str) -> TableDef:
        m = _TABLE_NAME_RE.search(desc)
        if m is None:
            raise FormatError('битое описание таблицы')
        td = TableDef(name=m.group(1))
        offset = 17 if '"RV"' in desc else 1
        for fname, ftype, fnull, flen, fprec, fcase in _FIELD_RE.findall(desc):
            null_exists = fnull == '1'
            size = (1 if null_exists else 0) + _field_size(ftype, int(flen))
            if ftype == 'RV':
                foffset = 1
            else:
                foffset = offset
                offset += size
            td.fields[fname] = FieldDef(
                fname, ftype, null_exists, int(flen), int(fprec),
                fcase == 'CS', foffset, size)
        td.row_length = max(offset, 5)
        fm = _FILES_RE.search(desc)
        if fm:
            td.data_page, td.blob_page, td.index_page = (int(x) for x in fm.groups())
        return td

    # ---- строки ----
    def table_rows(self, table: TableDef) -> Iterator[bytes]:
        if not table.data_page:
            return  # схема без данных (пустая таблица) — как в table_stats
        data = self.read_object(table.data_page)
        rl = table.row_length
        for i in range(0, len(data) - len(data) % rl, rl):
            yield data[i:i + rl]

    def read_blob(self, table: TableDef, first_chunk: int, size: int) -> bytes:
        """Чтение blob-цепочки таблицы (данные blob-таблицы кешируются с
        лимитом объёма — при переполнении кеш очищается)."""
        if size <= 0:
            return b''
        data = self._blob_cache.get(table.blob_page)
        if data is None:
            data = self.read_object(table.blob_page)
            if (self._blob_cache_bytes + len(data)) > self._blob_cache_max:
                # защита от переполнения памяти: сбрасываем кеш целиком
                # (blob-таблицы крупные, LRU не окупается)
                self._blob_cache = {}
                self._blob_cache_bytes = 0
            self._blob_cache[table.blob_page] = data
            self._blob_cache_bytes += len(data)
        out: list[bytes] = []
        pos = first_chunk
        remaining = size
        seen: set[int] = set()
        while remaining > 0 and pos and pos not in seen:
            seen.add(pos)
            block = data[pos * BLOB_CHUNK:(pos + 1) * BLOB_CHUNK]
            if len(block) < 6:
                break
            nxt, chunk_size = struct.unpack('<Ih', block[:6])
            out.append(block[6:6 + chunk_size])
            remaining -= chunk_size
            if nxt == 0:
                break
            pos = nxt
        return b''.join(out)[:size]

    # ---- DBSCHEMA ----
    def read_dbschema(self) -> str:
        table = self.tables['DBSCHEMA']
        f = table.fields['SERIALIZEDDATA']
        for row in self.table_rows(table):
            if row[:1] == b'\x01':
                continue
            off, size = struct.unpack('<2I', row[f.offset:f.offset + 8])
            return self.read_blob(table, off, size).decode('utf-8-sig')
        raise FormatError('DBSCHEMA пуст')

    # ---- DBNames (привязка GUID ↔ таблица) ----
    def read_dbnames(self) -> dict[str, tuple[str, int]]:
        if self._dbnames is None:
            raw = self.config_get('DBNames')
            if raw is None:
                raise FormatError('DBNames не найден в PARAMS')
            text = raw.decode('utf-8-sig')
            # GUID может встречаться несколько раз: основная таблица
            # ("Reference",74) и таблица изменений ("ReferenceChngR",1731).
            # Нужна запись с основным kind (приоритет по убыванию).
            best: dict[str, tuple[str, int, int]] = {}
            for g, kind, num in _DBNAME_RE.findall(text):
                pri = _DBNAME_PRIORITY.get(kind, 0)
                prev = best.get(g)
                if prev is None or pri > prev[2]:
                    best[g] = (kind, int(num), pri)
            self._dbnames = {g: (kind, num) for g, (kind, num, _) in best.items()}
        return self._dbnames

    # ---- конфигурация (CONFIG + CONFIGSAVE) ----
    def _load_config_rows(self) -> list[tuple[TableDef, str, int, int]]:
        """Строки CONFIG/CONFIGSAVE/PARAMS: (таблица, имя, смещение, размер).

        Blob-данные не читаются — только указатели (быстро: ~0.1s на 47k
        файлов). Реальное чтение — лениво, по запросу.
        """
        if self._config_raw is None:
            rows: list[tuple[TableDef, str, int, int]] = []
            for tname in ('CONFIG', 'CONFIGSAVE', 'PARAMS'):
                if tname not in self.tables:
                    continue
                t = self.tables[tname]
                f = t.fields
                for row in self.table_rows(t):
                    if row[:1] == b'\x01':
                        continue
                    nm = decode_nvc(row[f['FILENAME'].offset:
                                        f['FILENAME'].offset + f['FILENAME'].size])
                    if not nm or any(ord(c) < 32 for c in nm):
                        continue
                    off, size = struct.unpack(
                        '<2I', row[f['BINARYDATA'].offset:
                                   f['BINARYDATA'].offset + 8])
                    rows.append((t, nm, off, size))
            self._config_raw = rows
        return self._config_raw

    def config_get(self, name: str) -> bytes | None:
        """Распакованный файл конфигурации по имени (лениво, с кешем)."""
        index = self._config_index()
        if self._config_inflated is None:
            self._config_inflated = {}
        hit = self._config_inflated.get(name)
        if hit is not None:
            return hit
        entry = index.get(name)
        if entry is None:
            return None
        t, off, size = entry
        hit = _inflate(self.read_blob(t, off, size))
        self._config_inflated[name] = hit
        return hit

    def _config_index(self) -> dict[str, tuple[TableDef, int, int]]:
        """Индекс файлов конфигурации: имя -> (таблица, смещение, размер)."""
        if self._config_index_ is None:
            index: dict[str, tuple[TableDef, int, int]] = {}
            for t, nm, off, size in self._load_config_rows():
                index[nm] = (t, off, size)
            self._config_index_ = index
        return self._config_index_


def _inflate(data: bytes) -> bytes:
    """Распаковка deflate-потока (raw, wbits=-15).

    Внимание: первый байт raw-deflate НЕ всегда 0x78 (проверено на 1C_8.3:
    47 627 из 47 648 файлов сжаты, префиксы 0x9c/0x94 — BTYPE=2). Попытка
    распаковки — единственный надёжный способ отличить сжатое от plain.
    """
    try:
        return zlib.decompress(data, -15)
    except zlib.error:
        return data


# ---------------------------------------------------------------------------
# Коллекции конфигурации и привязка к таблицам
# ---------------------------------------------------------------------------

# class_guid (8.1-эпоха) -> тип объекта
_COLLECTION_CLASS: dict[str, str] = {
    'cf4abea6-37b2-11d4-940f-008048da11f9': 'Справочник',
    '061d872a-5787-460e-95ac-ed74ea3a3e84': 'Документ',
    'f6a80749-5ad7-400b-8519-39dc5dff2542': 'Перечисление',
    '13134201-f60b-11d5-a3c7-0050bae0a776': 'РегистрСведений',
    'b64d9a40-1642-11d6-a3c7-0050bae0a776': 'РегистрНакопления',
    '238e7e88-3c5f-48b2-8a3b-81ebbecb20ed': 'ПланСчетов',
}

# kind из DBNames -> префикс имени таблицы
_TABLE_PREFIX: dict[str, str] = {
    'Reference': 'REFERENCE', 'Document': 'DOCUMENT', 'Enum': 'ENUM',
    'InfoRg': 'INFORG', 'AccumRg': 'ACCUMRG', 'Acc': 'ACC',
    'CKinds': 'CKINDS', 'VT': 'VT',
}


def _lookup_table(tables: Mapping[str, TableDef], canonical: str) -> str:
    """Фактическое имя таблицы из dict `tables`, нечувствительно к регистру.

    Каноническое имя (header-регистр, напр. `_DOCUMENT625`) может не совпасть
    с физическим (TitleCase `_Document625`) в базах 8.3. Возвращает ключ
    (фактическое имя) или '' при отсутствии.
    """
    if not canonical:
        return ''
    if canonical in tables:
        return canonical
    low = canonical.lower()
    for k in tables:
        if k.lower() == low:
            return k
    return ''

# Приоритет kind из DBNames при дублях GUID: основная таблица важнее
# служебных (таблицы изменений, полей, индексов). 8.3 пишет для одного GUID
_DBNAME_PRIORITY: dict[str, int] = {
    'Reference': 100, 'Document': 100, 'Enum': 100, 'InfoRg': 100,
    'AccumRg': 100, 'Acc': 100, 'CKinds': 100, 'VT': 100, 'Const': 100,
    'Chrc': 100, 'DocumentJournal': 100, 'Seq': 100, 'CRg': 100,
    'AccRg': 100, 'RefSInf': 100, 'ExtDim': 100,
    'ReferenceChngR': 10, 'DocumentChngR': 10, 'EnumChngR': 10,
    'InfoRgChngR': 10, 'AccumRgChngR': 10, 'ConstChngR': 10,
    'ChrcChngR': 10, 'SeqChngR': 10, 'CRgChngR': 10, 'AccRgChngR': 10,
    'CKindsChngR': 10, 'ConfigChngR': 10,
}

# системные поля таблиц объектов (справочники/документы) — маппинг на имена 1С
_SYSTEM_FIELDS: dict[str, str] = {
    '_IDRREF': 'ID', '_VERSION': 'Версия', '_MARKED': 'ПометкаУдаления',
    '_ISMETADATA': 'Предопределённый', '_PARENTIDRREF': 'Родитель',
    '_FOLDER': 'ЭтоГруппа', '_CODE': 'Код', '_DESCRIPTION': 'Наименование',
    '_PREDEFINED': 'Предопределённый', '_PREDEFINEDID': 'ПредопределённыйID',
    '_NUMBER': 'Номер', '_DATE': 'Дата', '_POSTED': 'Проведён',
    '_RECORDER': 'Регистратор', '_ACTIVE': 'Активность',
    '_PERIOD': 'Период', '_KIND': 'Вид', '_LINENO': 'НомерСтроки',
    '_OWNERIDRREF': 'Владелец', '_NEWREF': 'НоваяСсылка',
}


def _is_guid(value: Any) -> bool:
    return isinstance(value, str) and _GUID_RE.fullmatch(value) is not None


def _find_collections(tree: Any) -> list[tuple[str, list[Any]]]:
    """Поиск узлов коллекций [class_guid, count, guid1, …] во всём дереве."""
    found: list[tuple[str, list[Any]]] = []
    stack: list[Any] = [tree]
    while stack:
        node = stack.pop()
        if not isinstance(node, list):
            continue
        if (len(node) >= 2 and isinstance(node[0], str) and _is_guid(node[0])
                and not isinstance(node[1], list)):
            try:
                count = int(str(node[1]))
            except ValueError:
                count = -1
            if count >= 0 and len(node) == count + 2:
                found.append((node[0].lower(), node))
        stack.extend(x for x in node if isinstance(x, list))
    return found


def _skip_ws(text: str, p: int, n: int) -> int:
    while p < n and text[p] in ' \t\r\n':
        p += 1
    return p


def _skip_quoted(text: str, p: int, n: int) -> int:
    """Пропустить строку в кавычках (без построения значения): вернуть позицию после."""
    p += 1
    while p < n:
        c = text[p]
        if c == '"':
            if p + 1 < n and text[p + 1] == '"':
                p += 2
                continue
            return p + 1
        if c == '\\' and _surrogate_cp(text, p) != -1:
            if (p + 10 < n and text[p + 5:p + 6] == '\\'
                    and _surrogate_cp(text, p + 5) != -1):
                p += 10
            else:
                p += 5
            continue
        p += 1
    return p


def _skip_value(text: str, p: int, n: int) -> int:
    """Пропустить одно значение (атом/список) без построения дерева."""
    depth = 0
    while p < n:
        c = text[p]
        if c == '"':
            p = _skip_quoted(text, p, n)
        elif c == '{':
            depth += 1
            p += 1
        elif c == '}':
            if depth == 0:
                return p  # список закончился: позиция на '}'
            depth -= 1
            p += 1
            if depth <= 0:
                return p
        elif c == ',' and depth == 0:
            return p  # разделитель элементов списка
        else:
            p += 1
    return p


def _atom_value(text: str, p: int, n: int) -> tuple[Any, int]:
    """Атомарное значение (строка/число) без рекурсии в списки."""
    if p >= n:
        return '', p
    if text[p] == '"':
        tok, p2 = _parse_quoted(text, p)
        return str(tok), p2
    s = p
    while p < n and text[p] not in ',}{ \t\r\n':
        p += 1
    return text[s:p], p


def _list_prefix(text: str, p: int, n: int, need: int) -> tuple[list[Any], int]:
    """Список: собрать первые need значений (списки — целиком), остальное пропустить."""
    p += 1
    items: list[Any] = []
    while True:
        p = _skip_ws(text, p, n)
        if p >= n:
            break
        if text[p] == '}':
            return items, p + 1
        if len(items) < need:
            if text[p] == '{':
                v, p = _list_prefix(text, p, n, 1_000_000)
            else:
                v, p = _atom_value(text, p, n)
            items.append(v)
        else:
            p = _skip_value(text, p, n)
        p = _skip_ws(text, p, n)
        if p < n and text[p] == ',':
            p += 1
    return items, p


def _object_name_fast(text: str) -> tuple[str, str]:
    """Имя/синоним объекта из текста скобкофайла без полного разбора.

    Разбирает только префикс дерева: корневой список, его второй элемент
    (список описаний) и первый подходящий элемент ['0', sub, …] — до
    синонима включительно. Остальное содержимое пропускается сканнером
    (без построения дерева) — на 8.3 это в ~10 раз быстрее parse_bracket.
    """
    n = len(text)
    p = 1 if text.startswith('\ufeff') else 0
    p = _skip_ws(text, p, n)
    if p >= n or text[p] != '{':
        return '', ''
    # корневой список: элемент 0 — атом, элемент 1 — список описаний
    p += 1
    _, p = _atom_value(text, _skip_ws(text, p, n), n)
    p = _skip_ws(text, p, n)
    if p >= n or text[p] != ',':
        return '', ''
    p = _skip_ws(text, p + 1, n)
    if p >= n or text[p] != '{':
        return '', ''
    p += 1  # список описаний
    while True:
        p = _skip_ws(text, p, n)
        if p >= n:
            return '', ''
        c = text[p]
        if c == '}':
            return '', ''
        name = syn = ''
        p2 = p
        if c == '{':
            # попытка: el = ['0', sub, …]
            q = _skip_ws(text, p + 1, n)
            v0, q = _atom_value(text, q, n)
            q = _skip_ws(text, q, n)
            if str(v0) == '0' and q < n and text[q] == ',':
                q = _skip_ws(text, q + 1, n)
                if q < n and text[q] == '{':
                    sub, p2 = _list_prefix(text, q, n, 4)
                    if len(sub) >= 4:
                        name = syn = ''
                        if (str(sub[0]) == '0'
                                or (isinstance(sub[1], list) and len(sub[1]) >= 3
                                    and str(sub[1][0]) == '1')):
                            name = str(sub[2])
                            sn = sub[3]
                            if isinstance(sn, list) and len(sn) >= 3:
                                syn = str(sn[2])
            if name or syn:
                return name, syn
            p = p2
            if p <= _skip_ws(text, p, n):
                p = _skip_value(text, p, n)
        else:
            p = _skip_value(text, p, n)
        p = _skip_ws(text, p, n)
        if p < n and text[p] == ',':
            p += 1


def _object_name(tree: Any) -> tuple[str, str]:
    """(имя, синоним) объекта из ['1', [...]] (8.1 и 8.3-форматы).

    8.1: ['0', ['0', <guid>, <имя>, [синонимы], …]]
    8.3: ['0', ['2', ['1','0',<guid>], <имя>, ['2','ru',<синоним>,…], …]]
    """
    if not isinstance(tree, list) or len(tree) < 2 or not isinstance(tree[1], list):
        return '', ''
    for el in tree[1]:
        if not (isinstance(el, list) and len(el) >= 2 and str(el[0]) == '0'
                and isinstance(el[1], list) and len(el[1]) >= 4):
            continue
        sub = el[1]
        name = ''
        syn = ''
        if str(sub[0]) == '0':
            # 8.1-эпоха: ['0', <guid>, <имя>, [синонимы], …]
            name = str(sub[2])
            syn_node = sub[3]
            if isinstance(syn_node, list) and len(syn_node) >= 3:
                syn = str(syn_node[2])
        elif isinstance(sub[1], list) and len(sub[1]) >= 3 and str(sub[1][0]) == '1':
            # 8.3: ['2', ['1','0',<guid>], <имя>, ['2','ru',<синоним>,…], …]
            name = str(sub[2])
            syn_node = sub[3]
            if isinstance(syn_node, list) and len(syn_node) >= 3:
                syn = str(syn_node[2])
        if name or syn:
            return name, syn
    return '', ''


# ---------------------------------------------------------------------------
# Публичный интерфейс (inspect_source / inspect_target / extract)
# ---------------------------------------------------------------------------


def read_metadata(path: str | Path) -> dict[str, Any]:
    """Метаданные ИБ 8.x -> единая модель: {objects: [ObjectType…], tables, locale}.

    Объекты конфигурации (CONFIG/DBNames) связываются с физическими таблицами
    по DBNames (kind + номер); поля — физические поля таблицы.
    Результат кешируется на диск (по признакам файла) и в памяти
    (LRU— повторные вызовы для одной и той же базы
    выполняются за миллисекунды.
    """
    p = Path(path)
    key = file_key(p)
    mem = _mem_meta_get(key)
    if mem is not None:
        return mem
    cache = _metadata_disk_cache()
    hit = cache.get_json(key, 'metadata')
    if isinstance(hit, dict):
        _mem_meta_put(key, hit)
        return hit  # type: ignore[no-any-return,unused-ignore]
    objects: list[dict[str, Any]] = []
    tables: list[str] = []
    locale = ''
    timings = Timings()
    try:
        db = Database1CD(p)
    except (FormatError, OSError) as exc:
        # понятная диагностика на битых/не-ИБ файлах ()
        raise FormatError(
            f'read_metadata({p}): файл повреждён или не является ИБ 8.x: '
            f'{exc}') from exc
    with db:
        tables = sorted(db.tables)
        locale = db.locale
        t0 = time.perf_counter()
        dbnames = db.read_dbnames()
        timings.record('read_dbnames', (time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        root = parse_bracket((db.config_get('root') or b'').decode('utf-8'))
        main_guid = str(root[1])
        main = parse_bracket((db.config_get(main_guid) or b'').decode('utf-8'))
        timings.record('read_config_root', (time.perf_counter() - t0) * 1000)

        for class_guid, node in _find_collections(main):
            kind = _COLLECTION_CLASS.get(class_guid)
            if kind is None:
                continue
            for guid in (str(g) for g in node[2:]):
                t_obj = time.perf_counter()
                raw = db.config_get(guid)
                if raw is None:
                    continue
                if not raw.lstrip(b'\xef\xbb\xbf').startswith(b'{'):
                    # не скобкофайл (JSON/бинарные данные) — пропустить
                    continue
                name, synonym = _object_name_fast(
                    raw.lstrip(b'\xef\xbb\xbf').decode('utf-8'))
                binding = dbnames.get(guid.lower())
                if binding is None:
                    continue
                db_kind, num = binding
                prefix = _TABLE_PREFIX.get(db_kind)
                table_name = f'_{prefix}{num}' if prefix else ''
                # физические имена таблиц 8.3 могут отличаться по регистру
                # (TitleCase: _Document625), а каноническое — верхний регистр
                actual = _lookup_table(db.tables, table_name)
                table = db.tables.get(actual) if actual else None
                if actual:
                    table_name = actual
                attrs: list[dict[str, Any]] = []
                if table is not None:
                    for fname, fdef in table.fields.items():
                        attrs.append({
                            'name': _SYSTEM_FIELDS.get(fname, fname),
                            'field': fname,
                            'type': _model_type(fdef),
                            'length': fdef.length,
                            'precision': fdef.precision,
                        })
                objects.append({
                    'kind': kind,
                    'name': name,
                    'synonym': synonym,
                    'table': table_name,
                    'ref_num': num,
                    'guid': guid,
                    'attributes': attrs,
                })
                timings.record(f'object:{kind}', (time.perf_counter() - t_obj) * 1000)
    result = {'objects': objects, 'tables': tables, 'locale': locale,
              'timings': timings.snapshot()}
    cache.put_json(key, 'metadata', result)
    _mem_meta_put(key, result)
    return result


# ---- in-memory LRU для read_metadata : MCP-сессии) ----
_MEM_META_MAX = 8
_mem_meta: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _mem_meta_get(key: str) -> dict[str, Any] | None:
    if key not in _mem_meta:
        return None
    _mem_meta.move_to_end(key)
    return _mem_meta[key]


def _mem_meta_put(key: str, value: dict[str, Any]) -> None:
    _mem_meta[key] = value
    _mem_meta.move_to_end(key)
    while len(_mem_meta) > _MEM_META_MAX:
        _mem_meta.popitem(last=False)


def _clear_mem_meta() -> None:
    _mem_meta.clear()


def _metadata_disk_cache() -> Cache:
    """Дисковый кеш метаданных (в памяти процесса — один экземпляр)."""
    global _METADATA_CACHE_INSTANCE
    if _METADATA_CACHE_INSTANCE is None:
        _METADATA_CACHE_INSTANCE = Cache()
    return _METADATA_CACHE_INSTANCE


def to_model(path: str | Path) -> list[ObjectType]:
    """read_metadata -> единая модель model.py (ObjectType/AttrDef)."""
    from .model import AttrDef, AttrType
    return [ObjectType(
        kind=o['kind'], name=o['name'], synonym=o['synonym'],
        attributes=[AttrDef(a['name'], AttrType(
            kind=a['type'], length=a.get('length', 0),
            precision=a.get('precision', 0)))
            for a in o['attributes']],
    ) for o in read_metadata(path)['objects']]


def _model_type(fdef: FieldDef) -> str:
    t = fdef.type
    if t in ('NVC', 'NC'):
        return 'string'
    if t in ('N', 'NT', 'I'):
        return 'number'
    if t == 'DT':
        return 'date'
    if t == 'L':
        return 'bool'
    if t in ('RV', 'B'):
        return 'ref'
    return 'unknown'


def read_table(path: str | Path, table_name: str,
               ref_tables: Mapping[str, str] | None = None) -> Iterator[dict[str, Any]]:
    """Потоковое чтение записей таблицы: имя поля -> декодированное значение.

    `ref_tables`: {имя_поля: имя_таблицы} — ссылочные поля (RV/B) разрешаются
    в `{'guid': …, 'name': …}`: имя объекта подставляется из таблицы-цели
    (кеш ссылок GUID→наименование строится лениво, один раз на таблицу).
    Без `ref_tables` ссылки отдаются GUID-строкой.
    """
    with Database1CD(path) as db:
        if table_name not in db.tables:
            raise KeyError(f'таблица не найдена: {table_name}')
        table = db.tables[table_name]
        for row in db.table_rows(table):
            rec: dict[str, Any] = {}
            for fname, fdef in table.fields.items():
                raw = row[fdef.offset:fdef.offset + fdef.size]
                val = decode_field(fdef, raw)
                if (ref_tables and fname in ref_tables
                        and fdef.type in ('RV', 'B')):
                    target = ref_tables[fname]
                    name = db.ref_name(target, raw) if target in db.tables else None
                    val = {'guid': val, 'name': name}
                rec[fname] = val
            yield rec


def read_dbschema(path: str | Path) -> str:
    """Текст DBSCHEMA (для отладки и маппинга FldNNN ↔ реквизиты)."""
    with Database1CD(path) as db:
        return db.read_dbschema()
