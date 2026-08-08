"""Unit-тесты прямой записи в 1CD (Фаза 10): create_1cd + append_records."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, enc_nc, encode_row
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import WriteError, append_records, create_1cd


def _fields() -> list[FixtureField]:
    return [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=150),
    ]


def _table(rows: list[bytes] | None = None) -> FixtureTable:
    return FixtureTable('_REFERENCE3', fields=_fields(),
                        rows=rows or [])


def _row(code: str, descr: str, marked: bool = False) -> bytes:
    return encode_row(_fields(), {
        '_MARKED': marked, '_CODE': code, '_DESCRIPTION': descr,
    })


def test_create_1cd_readable(tmp_path: Path):
    """Созданная база читается собственным парсером; структура совпадает."""
    p = create_1cd(tmp_path / 'new.1CD', [_table()])
    assert p.is_file()
    with Database1CD(p) as db:
        assert '_REFERENCE3' in db.tables
        t = db.tables['_REFERENCE3']
        assert set(t.fields) == {'_VERSION', '_IDRREF', '_MARKED', '_CODE',
                                 '_DESCRIPTION'}


def test_create_1cd_empty_table_has_no_data(tmp_path: Path):
    """Пустая таблица (без строк) не имеет объекта данных."""
    p = create_1cd(tmp_path / 'new.1CD', [_table()])
    with Database1CD(p) as db:
        assert db.tables['_REFERENCE3'].data_page == 0


def test_append_records_roundtrip(tmp_path: Path):
    """Записанные строки декодируются парсером обратно без потерь."""
    base = _table(rows=[_row('00001', 'Товар А')])
    p = create_1cd(tmp_path / 'db.1CD', [base])
    n = append_records(p, '_REFERENCE3', _row('00002', 'Товар Б')
                       + _row('00003', 'Товар В', marked=True))
    assert n == 3
    with Database1CD(p) as db:
        rows = list(db.table_rows(db.tables['_REFERENCE3']))
    assert len(rows) == 3
    f = db.tables['_REFERENCE3'].fields
    assert rows[0][f['_CODE'].offset:f['_CODE'].offset + f['_CODE'].size] \
        == enc_nc('00001', f['_CODE'].length)
    assert rows[2][f['_MARKED'].offset] == 1


def test_append_records_unknown_table(tmp_path: Path):
    p = create_1cd(tmp_path / 'db.1CD', [_table()])
    with pytest.raises(WriteError, match='таблица не найдена'):
        append_records(p, 'NOPE', b'\x00' * 5)


def test_append_records_empty_table_rejected(tmp_path: Path):
    """data_page == 0 — явная ошибка, а не молчаливая порча."""
    p = create_1cd(tmp_path / 'db.1CD', [_table()])
    with pytest.raises(WriteError, match='без объекта данных'):
        append_records(p, '_REFERENCE3', _row('00001', 'Товар А'))
