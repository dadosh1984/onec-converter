"""Интеграционный тест прямой записи на КОПИИ реальной базы 8.1 (Фаза 10).

Копия исходника → append тестовых записей → чтение парсером, размеры
сходятся. Оригинал не изменяется (пишем только в tmp-копию).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import append_records, copy_1cd

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует (read-only копия)')

TABLE = '_REFERENCE3'


@REQUIRED
@pytest.mark.integration
def test_append_to_fat_level1_on_copy(tmp_path: Path):
    """Копия 8.1 → append в fat_level 1 таблицу (>8 МБ) → чтение без потерь."""
    import struct

    with Database1CD(BASE_81) as db:
        fl1 = [n for n, t in db.tables.items()
               if t.data_page and struct.unpack(
                   '<H', db.read_page(t.data_page)[2:4])[0] == 1]
    if not fl1:
        pytest.skip('в базе 8.1 нет таблиц с fat_level 1')
    tab = fl1[0]

    cp = copy_1cd(BASE_81, tmp_path / 'copy_fl1.1CD')
    with Database1CD(BASE_81) as db:
        rl = db.tables[tab].row_length
        rows_before = db.table_stats(tab)[0]

    add_rows = b'\x00' * rl * 2
    n = append_records(cp, tab, add_rows)
    assert n == rows_before + 2
    with Database1CD(cp) as db:
        assert db.table_stats(tab)[0] == rows_before + 2
        assert db.tables[tab].row_length == rl
    # структура объекта осталась fat_level 1
    with Database1CD(cp) as db:
        dp = db.tables[tab].data_page
        assert struct.unpack('<H', db.read_page(dp)[2:4])[0] == 1


@REQUIRED
@pytest.mark.integration
def test_append_on_copy_of_real_base(tmp_path: Path):
    """Копия 8.1 → append 2 строк → парсер читает, размеры сходятся."""
    cp = copy_1cd(BASE_81, tmp_path / 'copy.1CD')
    assert cp.is_file() and cp.stat().st_size == BASE_81.stat().st_size

    with Database1CD(BASE_81) as db:
        t0 = db.tables[TABLE]
        rows0 = list(db.table_rows(t0))
        rl = t0.row_length
    with Database1CD(cp) as db:
        assert db.tables[TABLE].data_page == t0.data_page

    # две нулевые строки фиксированной длины (декодируются как пустые)
    n = append_records(cp, TABLE, b'\x00' * rl * 2)
    assert n == len(rows0) + 2

    with Database1CD(cp) as db:
        t1 = db.tables[TABLE]
        rows1 = list(db.table_rows(t1))
        assert len(rows1) == len(rows0) + 2
        assert db.table_stats(TABLE)[0] == len(rows1)


@REQUIRED
@pytest.mark.integration
def test_original_untouched(tmp_path: Path):
    """Оригинал после append в копию не изменяется; копия растёт."""
    cp = copy_1cd(BASE_81, tmp_path / 'copy.1CD')
    before = BASE_81.stat().st_size
    with Database1CD(BASE_81) as db:
        t0 = db.tables[TABLE]
        rl = t0.row_length
        rows0 = list(db.table_rows(t0))
    # много строк — заведомо на несколько страниц (последняя страница неполная)
    n = append_records(cp, TABLE, b'\x00' * rl * 3000)
    assert BASE_81.stat().st_size == before
    assert cp.stat().st_size >= before + 8192  # добавились страницы данных
    with Database1CD(cp) as db:
        assert len(list(db.table_rows(db.tables[TABLE]))) == len(rows0) + 3000
    assert n == len(rows0) + 3000
