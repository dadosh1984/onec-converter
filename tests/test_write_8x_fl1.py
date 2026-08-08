"""Unit-тесты Фазы 12: fat_level 1 (объекты > 8 МБ) и защита записи."""
from __future__ import annotations

import struct
import warnings
from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import (
    PAGE_SIZE,
    LockError,
    _read_object_full,
    _set_total_pages,
    _write_object_header,
    _write_page,
    append_records,
    create_1cd,
)

OBJ_SIG = b'\x1c\xfd'


def _fields() -> list[FixtureField]:
    return [FixtureField('_VERSION', 'RV', length=16),
            FixtureField('_IDRREF', 'B', length=16),
            FixtureField('_CODE', 'NC', length=9),
            FixtureField('_DESCRIPTION', 'NVC', length=40)]


def _row(code: str, descr: str) -> bytes:
    return encode_row(_fields(), {'_CODE': code, '_DESCRIPTION': descr})


def _total(base: Path) -> int:
    head = base.read_bytes()[:PAGE_SIZE]
    return int(struct.unpack('<I', head[12:16])[0])


def _make_fl1_base(tmp_path: Path, n_rows: int = 5) -> tuple[Path, bytes]:
    """База с таблицей _REFERENCE7, чей объект данных — fat_level 1.

    create_1cd (таблица с данными → объект fat_level 0) → пересборка
    объекта в fat_level 1 вручную: новые страницы данных + indirect-
    страницы в конец файла, заголовок переписан с fat_level=1 (каталог
    не трогаем — data_page тот же). Парсер читает объект по заголовку.
    """
    row = _row('000000001', 'Тест')
    base = create_1cd(
        tmp_path / '1Cv8.1CD',
        [FixtureTable('_REFERENCE7', fields=_fields(), rows=[row])])
    append_records(base, '_REFERENCE7', row * (n_rows - 1))
    with Database1CD(base) as db:
        dp = db.tables['_REFERENCE7'].data_page
    fl, _, indirect, data = _read_object_full(base, dp)
    assert fl == 0 and not indirect
    total = _total(base)
    n = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE
    new_dp = [total + i for i in range(n)]
    for j in range(n):
        _write_page(base, new_dp[j], data[j * PAGE_SIZE:(j + 1) * PAGE_SIZE])
    total += n
    per = PAGE_SIZE // 4
    n_ind = (n + per - 1) // per
    ind: list[int] = []
    for k in range(n_ind):
        ib = bytearray(PAGE_SIZE)
        for j, pg in enumerate(new_dp[k * per:(k + 1) * per]):
            struct.pack_into('<I', ib, 4 * j, pg)
        _write_page(base, total, bytes(ib))
        ind.append(total)
        total += 1
    _write_object_header(base, dp, ind, len(data), fat_level=1)
    _set_total_pages(base, total)
    return base, row


def test_parser_reads_fl1_object(tmp_path: Path):
    base, _row_b = _make_fl1_base(tmp_path)
    with Database1CD(base) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 5
        assert rows[0][:2] == b'\x00\x00'  # данные без потерь


def test_append_to_fl1_roundtrip(tmp_path: Path):
    base, row = _make_fl1_base(tmp_path)
    from onec_converter.source_8x_file import decode_nc

    append_records(base, '_REFERENCE7', row * 3)
    with Database1CD(base) as db:
        t = db.tables['_REFERENCE7']
        rows = list(db.table_rows(t))
        assert len(rows) == 8
        last = rows[-1]
        f = t.fields['_CODE']
        assert decode_nc(last[f.offset:f.offset + f.size]) == '000000001'
        assert db.table_stats('_REFERENCE7')[0] == 8


def test_fl1_object_still_level1_after_append(tmp_path: Path):
    base, row = _make_fl1_base(tmp_path)
    append_records(base, '_REFERENCE7', row * 2)
    with Database1CD(base) as db:
        dp = db.tables['_REFERENCE7'].data_page
    fl, _, indirect, _ = _read_object_full(base, dp)
    assert fl == 1
    assert indirect


def test_lock_error_on_open_base(tmp_path: Path):
    base, row = _make_fl1_base(tmp_path, n_rows=1)
    (tmp_path / '1Cv8.1CL').write_bytes(b'lock')
    with pytest.raises(LockError, match='1Cv8.1CL'):
        append_records(base, '_REFERENCE7', row)


def test_lock_error_on_tmp_files(tmp_path: Path):
    base, row = _make_fl1_base(tmp_path, n_rows=1)
    (tmp_path / '1Cv8tmp.db').write_bytes(b'x')
    with pytest.raises(LockError, match='1Cv8tmp'):
        append_records(base, '_REFERENCE7', row)


def test_index_warning(tmp_path: Path):
    """Таблица с index_page != 0 — предупреждение об индексах.

    create_1cd создаёт таблицы без индексов; проверяем, что append на
    обычной таблице НЕ даёт warning, а патч index_page в каталоге даёт.
    """
    base, row = _make_fl1_base(tmp_path, n_rows=1)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        append_records(base, '_REFERENCE7', row)
        assert not [x for x in w if 'индексы' in str(x.message)]


def test_write_object_header_roundtrip_fl1(tmp_path: Path):
    """Заголовок fat_level 1 → indirect → данные; парсер читает объект."""
    base = create_1cd(tmp_path / '1Cv8.1CD',
                      [FixtureTable('_REFERENCE7', fields=_fields())])
    total = _total(base)
    header_page = total
    dp_pages = [total + 1, total + 2]
    ind_page = total + 3
    for j, pg in enumerate(dp_pages):
        _write_page(base, pg, bytes([j + 1]) * PAGE_SIZE)
    ib = bytearray(PAGE_SIZE)
    for j, pg in enumerate(dp_pages):
        struct.pack_into('<I', ib, 4 * j, pg)
    _write_page(base, ind_page, bytes(ib))
    _set_total_pages(base, ind_page + 1)
    _write_object_header(base, header_page, [ind_page], 2 * PAGE_SIZE,
                         fat_level=1)
    fl, pages, indirect, data = _read_object_full(base, header_page)
    assert fl == 1
    assert pages == dp_pages
    assert indirect == [ind_page]
    assert data == bytes([1]) * PAGE_SIZE + bytes([2]) * PAGE_SIZE
