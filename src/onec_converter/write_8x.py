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
import warnings
from pathlib import Path

from .fake_1cd import FixtureTable, build_fake_1cd
from .source_8x_file import Database1CD

PAGE_SIZE = 8192
PAGE_HEADER_SIZE = 24
OBJ_SIG = b'\x1c\xfd'


class WriteError(Exception):
    """Ошибка прямой записи в 1CD."""


class LockError(WriteError):
    """База открыта/используется — запись запрещена (Фаза 12)."""


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
    """Запись страницы; неполные данные дополняются нулями до page_size,
    чтобы размер файла всегда оставался кратным странице (требование 1С)."""
    if len(data) < page_size:
        data = data + b'\x00' * (page_size - len(data))
    with open(path, 'r+b') as f:
        f.seek(num * page_size)
        f.write(data[:page_size])


def _read_object(path: Path, header_page: int,
                 page_size: int = PAGE_SIZE) -> tuple[list[int], bytes]:
    """FAT-список страниц и данные объекта (fat_level 0/1).

    Возвращает (страницы данных, данные) — для записи используйте
    `_read_object_full` (нужны также indirect-страницы).
    """
    _, pages, _, data = _read_object_full(path, header_page, page_size)
    return pages, data


def _read_object_full(path: Path, header_page: int,
                      page_size: int = PAGE_SIZE) \
        -> tuple[int, list[int], list[int], bytes]:
    """(fat_level, страницы данных, indirect-страницы, данные) объекта."""
    buf = _read_page(path, header_page, page_size)
    if buf[:2] != OBJ_SIG:
        raise WriteError(f'не объект БД на странице {header_page}: {buf[:2].hex()}')
    fat_level = struct.unpack('<H', buf[2:4])[0]
    length = struct.unpack('<Q', buf[16:24])[0]
    entries = (page_size - PAGE_HEADER_SIZE) // 4
    fat = struct.unpack(f'<{entries}I', buf[PAGE_HEADER_SIZE:])
    if fat_level == 0:
        indirect: list[int] = []
        pages = [p for p in fat if p != 0]
        pages = pages[: (length + page_size - 1) // page_size]
    elif fat_level == 1:
        indirect = [ip for ip in fat if ip != 0]
        pages = []
        for ip in indirect:
            ibuf = _read_page(path, ip, page_size)
            for v in struct.unpack(f'<{page_size // 4}I', ibuf):
                if v == 0:
                    break
                pages.append(v)
    else:
        raise WriteError(f'fat_level {fat_level} не поддерживается (0/1)')
    data = b''.join(_read_page(path, p, page_size) for p in pages)
    return fat_level, pages, indirect, data[:length]


def _write_object_header(path: Path, header_page: int, pages: list[int],
                         length: int, fat_level: int = 0,
                         page_size: int = PAGE_SIZE) -> None:
    """Запись заголовка объекта: сигнатура, fat_level, длина, FAT.

    fat_level 0 — FAT из номеров страниц данных; fat_level 1 — FAT из
    номеров indirect-страниц (каждая содержит номера страниц данных).
    """
    header = bytearray(page_size)
    header[0:2] = OBJ_SIG
    struct.pack_into('<H', header, 2, fat_level)
    struct.pack_into('<Q', header, 16, length)
    if fat_level == 0 or fat_level == 1:
        for j, p in enumerate(pages):
            struct.pack_into('<I', header, PAGE_HEADER_SIZE + 4 * j, p)
    else:
        raise WriteError(f'fat_level {fat_level} не поддерживается (0/1)')
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


def _ensure_not_locked(path: Path) -> None:
    """Отказ, если база открыта в 1С (1Cv8.1CL) или используется (1Cv8tmp*)."""
    d = path.parent
    if (d / '1Cv8.1CL').exists():
        raise LockError(f'база открыта (1Cv8.1CL) — запись запрещена: {path}')
    if list(d.glob('1Cv8tmp*')):
        raise LockError(f'база используется (1Cv8tmp*) — запись запрещена: {path}')


def overwrite_row(path: str | Path, table_name: str, row_index: int,
                  row_bytes: bytes) -> None:
    """Перезапись строки таблицы по позиции (для регистров без _IDRREF).

    Длина строки не меняется; позиция — индекс строки в data-объекте
    (начиная с 0, включая служебные). Ошибки формата -> WriteError.
    """
    p = Path(path)
    with Database1CD(p) as db:
        if table_name not in db.tables:
            raise WriteError(f'таблица не найдена: {table_name}')
        t = db.tables[table_name]
        if not t.data_page:
            raise WriteError(f'таблица {table_name!r} без объекта данных '
                             f'(data_page=0): обновление не поддерживается')
        row_length = t.row_length or 1
        if len(row_bytes) != row_length:
            raise WriteError(f'длина строки {len(row_bytes)} != '
                             f'row_length={row_length}')
    _ensure_not_locked(p)
    _, pages, _, data = _read_object_full(p, t.data_page)
    if len(data) < (row_index + 1) * row_length:
        raise WriteError(f'строка {row_index} вне данных таблицы {table_name!r}')
    new_data = (data[:row_index * row_length] + row_bytes
                + data[(row_index + 1) * row_length:])
    n_pages = (len(new_data) + PAGE_SIZE - 1) // PAGE_SIZE
    for j in range(n_pages):
        _write_page(p, pages[j], new_data[j * PAGE_SIZE:(j + 1) * PAGE_SIZE])


def update_record(path: str | Path, table_name: str, idref: bytes,
                  row_bytes: bytes) -> bool:
    """Перезапись существующей строки таблицы по _IDRREF (Фаза bridge).

    Длина строки не меняется — переписываются только страницы данных объекта
    (FAT и заголовок не трогаются). Строка не найдена (или _IDRREF = 0) ->
    False. Таблица без объекта данных / без _IDRREF / неверная длина строки
    -> WriteError. Открытая ИБ (1Cv8.1CL/1Cv8tmp*) -> LockError.
    """
    p = Path(path)
    with Database1CD(p) as db:
        if table_name not in db.tables:
            raise WriteError(f'таблица не найдена: {table_name}')
        t = db.tables[table_name]
        if not t.data_page:
            raise WriteError(f'таблица {table_name!r} без объекта данных '
                             f'(data_page=0): обновление не поддерживается')
        row_length = t.row_length or 1
        if len(row_bytes) != row_length:
            raise WriteError(f'длина строки {len(row_bytes)} != '
                             f'row_length={row_length}')
        idr = t.fields.get('_IDRREF')
        if idr is None:
            raise WriteError(f'таблица {table_name!r} без поля _IDRREF')
        idx = -1
        for i, row in enumerate(db.table_rows(t)):
            if row[:1] == b'\x01' or len(row) < 16:
                continue
            if row[idr.offset:idr.offset + 16] == idref:
                idx = i
                break
        if idx < 0:
            return False
    overwrite_row(p, table_name, idx, row_bytes)
    return True


def append_records(path: str | Path, table_name: str, rows: bytes) -> int:
    """Добавление строк в конец таблицы; возвращает новое число строк.

    Дописывает страницы данных в конец файла, обновляет FAT (level 0/1)
    и длину объекта таблицы, total_pages в заголовке. Таблица без объекта
    данных (data_page == 0) не поддерживается — WriteError. Открытая ИБ
    (1Cv8.1CL/1Cv8tmp*) — LockError. Индексы не пересобираются — warning.
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
        if t.index_page:
            warnings.warn(f'таблица {table_name!r} имеет индексы (index_page='
                          f'{t.index_page}) — индексы не пересобираются',
                          UserWarning, stacklevel=2)

    _ensure_not_locked(p)
    total = _total_pages(p)
    fat_level, pages, _, data = _read_object_full(p, t.data_page)
    new_data = data + rows
    n_pages = (len(new_data) + PAGE_SIZE - 1) // PAGE_SIZE
    need = n_pages - len(pages)
    if need < 0:
        raise WriteError('нельзя уменьшить таблицу')
    new_pages = pages + list(range(total, total + need))
    total += need
    # перезаписываем все страницы объекта: последняя страница могла быть
    # неполной, и новые байты могли частично влезть в неё (need == 0)
    for j in range(n_pages):
        _write_page(p, new_pages[j],
                    new_data[j * PAGE_SIZE:(j + 1) * PAGE_SIZE])
    entries = (PAGE_SIZE - PAGE_HEADER_SIZE) // 4
    # переход fat_level 0 -> 1, если FAT не влезает в заголовок
    if fat_level == 0 and n_pages > entries:
        per = PAGE_SIZE // 4
        n_ind = (n_pages + per - 1) // per
        if n_ind > entries:
            raise WriteError(f'нужен fat_level 2 ({n_ind} indirect > {entries} '
                             f'слотов): таблица {table_name!r} слишком большая')
        new_ind: list[int] = []
        for k in range(n_ind):
            ibuf = bytearray(PAGE_SIZE)
            for j, pg in enumerate(new_pages[k * per:(k + 1) * per]):
                struct.pack_into('<I', ibuf, 4 * j, pg)
            _write_page(p, total, bytes(ibuf))
            new_ind.append(total)
            total += 1
        _write_object_header(p, t.data_page, new_ind, len(new_data),
                             fat_level=1)
    elif fat_level == 0:
        _write_object_header(p, t.data_page, new_pages, len(new_data))
    elif fat_level == 1:
        # indirect-страницы: page_size/4 номеров данных на страницу-указатель
        per = PAGE_SIZE // 4
        n_ind = (n_pages + per - 1) // per
        entries = (PAGE_SIZE - PAGE_HEADER_SIZE) // 4
        if n_ind > entries:
            raise WriteError(f'нужен fat_level 2 ({n_ind} indirect > {entries} '
                             f'слотов): таблица {table_name!r} слишком большая')
        new_ind1: list[int] = []
        for k in range(n_ind):
            ibuf = bytearray(PAGE_SIZE)
            for j, pg in enumerate(new_pages[k * per:(k + 1) * per]):
                struct.pack_into('<I', ibuf, 4 * j, pg)
            _write_page(p, total, bytes(ibuf))
            new_ind1.append(total)
            total += 1
        _write_object_header(p, t.data_page, new_ind1, len(new_data),
                             fat_level=1)
    else:
        raise WriteError(f'fat_level {fat_level} не поддерживается (0/1)')
    _set_total_pages(p, total)
    return len(new_data) // row_length
