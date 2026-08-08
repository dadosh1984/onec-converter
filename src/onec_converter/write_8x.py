"""Прямая запись в 1CD 8.3 (Фаза 10): создание базы и добавление записей.

Работаем ТОЛЬКО на копиях баз — никогда на оригиналах. Формат по
docs/format-8x.md (раздел «Запись»): заголовок (1CDBMSV8, страницы 8192),
root-объект (стр. 2) с каталогом таблиц в blob-цепочках, объекты данных
таблиц (fat_level 0/1). Создание базы переиспользует layout build_fake_1cd;
навигация по существующей базе — структуру TableDef из source_8x_file.

Инкрементальная запись (append_records) дописывает страницы данных в конец
файла и обновляет: FAT level 0 и длину объекта таблицы, total_pages в
заголовке файла. Таблицы без объекта данных (data_page == 0) не поддерживаются.
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

from .fake_1cd import FixtureTable, build_fake_1cd
from .source_8x_file import Database1CD

PAGE_SIZE = 8192
PAGE_HEADER_SIZE = 24
OBJ_SIG = b'\x1c\xfd'


class WriteError(Exception):
    """Ошибка прямой записи в 1CD."""


def copy_1cd(src: str | Path, dst: str | Path) -> Path:
    """Копия базы для записи — оригинал никогда не изменяется."""
    p = Path(dst)
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, p)
    return p


def create_1cd(path: str | Path, tables: list[FixtureTable]) -> Path:
    """Новая пустая база 1CD: структура (таблицы/поля), данных нет."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(build_fake_1cd(tables))
    return p


# ---------------------------------------------------------------------------
# Низкоуровневые операции со страницами (read-only парсер не пишет)
# ---------------------------------------------------------------------------


def _read_page(path: Path, num: int, page_size: int = PAGE_SIZE) -> bytes:
    with open(path, 'rb') as f:
        f.seek(num * page_size)
        return f.read(page_size)


def _write_page(path: Path, num: int, data: bytes, page_size: int = PAGE_SIZE) -> None:
    with open(path, 'r+b') as f:
        f.seek(num * page_size)
        f.write(data[:page_size])


def _read_object(path: Path, header_page: int,
                 page_size: int = PAGE_SIZE) -> tuple[list[int], bytes]:
    """FAT-список страниц и данные объекта по странице-заголовку (level 0)."""
    buf = _read_page(path, header_page, page_size)
    if buf[:2] != OBJ_SIG:
        raise WriteError(f'не объект БД на странице {header_page}: {buf[:2].hex()}')
    fat_level = struct.unpack('<H', buf[2:4])[0]
    if fat_level != 0:
        raise WriteError(f'fat_level {fat_level} не поддерживается (только 0)')
    length = struct.unpack('<Q', buf[16:24])[0]
    entries = (page_size - PAGE_HEADER_SIZE) // 4
    fat = struct.unpack(f'<{entries}I', buf[PAGE_HEADER_SIZE:])
    pages = [p for p in fat if p != 0]
    pages = pages[: (length + page_size - 1) // page_size]
    data = b''.join(_read_page(path, p, page_size) for p in pages)
    return pages, data[:length]


def _write_object_header(path: Path, header_page: int, pages: list[int],
                         length: int, page_size: int = PAGE_SIZE) -> None:
    """Запись заголовка объекта: сигнатура, fat_level 0, длина, FAT."""
    header = bytearray(page_size)
    header[0:2] = OBJ_SIG
    struct.pack_into('<H', header, 2, 0)           # fat_level
    struct.pack_into('<Q', header, 16, length)
    for j, p in enumerate(pages):
        struct.pack_into('<I', header, PAGE_HEADER_SIZE + 4 * j, p)
    _write_page(path, header_page, bytes(header), page_size)


def _total_pages(path: Path, page_size: int = PAGE_SIZE) -> int:
    head = _read_page(path, 0, page_size)
    return int(struct.unpack('<I', head[12:16])[0])


def _set_total_pages(path: Path, total: int, page_size: int = PAGE_SIZE) -> None:
    with open(path, 'r+b') as f:
        f.seek(12)
        f.write(struct.pack('<I', total))


# ---------------------------------------------------------------------------
# Добавление записей
# ---------------------------------------------------------------------------


def append_records(path: str | Path, table_name: str, rows: bytes) -> int:
    """Добавление строк в конец таблицы; возвращает новое число строк.

    Дописывает страницы данных в конец файла, обновляет FAT level 0 и длину
    объекта таблицы, total_pages в заголовке. Таблица без объекта данных
    (data_page == 0) не поддерживается — WriteError.
    """
    p = Path(path)
    with Database1CD(p) as db:
        if table_name not in db.tables:
            raise WriteError(f'таблица не найдена: {table_name}')
        t = db.tables[table_name]
        if not t.data_page:
            raise WriteError(f'таблица {table_name!r} без объекта данных '
                             f'(data_page=0): добавление строк не поддерживается')
        row_length = t.row_length or 1
        if len(rows) % row_length:
            raise WriteError(f'длина строк {len(rows)} не кратна '
                             f'row_length={row_length}')

    total = _total_pages(p)
    pages, data = _read_object(p, t.data_page)
    new_data = data + rows
    n_pages = (len(new_data) + PAGE_SIZE - 1) // PAGE_SIZE
    need = n_pages - len(pages)
    if need < 0:
        raise WriteError('нельзя уменьшить таблицу')
    new_pages = pages + list(range(total, total + need))
    # перезаписываем все страницы объекта: последняя страница могла быть
    # неполной, и новые байты могли частично влезть в неё (need == 0)
    for j in range(n_pages):
        _write_page(p, new_pages[j],
                    new_data[j * PAGE_SIZE:(j + 1) * PAGE_SIZE])
    _write_object_header(p, t.data_page, new_pages, len(new_data))
    _set_total_pages(p, total + need)
    return len(new_data) // row_length
