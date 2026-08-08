"""Фаза 14 (Вариант A): поведение append_records для индексированных таблиц
сохранено. Запись индекса не реализуется, поэтому UserWarning
«индексы не пересобираются» для таблиц с index_page != 0 остаётся.
Тест на реальной копии 8.1 подтверждает сохранение ограничения.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import append_records, copy_1cd

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует (read-only)')


@REQUIRED
@pytest.mark.integration
def test_indexed_table_still_warns_on_append(tmp_path: Path):
    """index_page != 0 → append выдаёт UserWarning («индексы не пересобираются»)."""
    cp = copy_1cd(BASE_81, tmp_path / 'copy.1CD')
    with Database1CD(cp) as db:
        t = db.tables['_REFERENCE3']
        assert t.index_page, 'у _REFERENCE3 должен быть индекс'
        rl = t.row_length
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        append_records(cp, '_REFERENCE3', b'\x00' * rl)
    assert any('индексы' in str(x.message) for x in w),         'append к индексированной таблице должен предупреждать об индексах'
