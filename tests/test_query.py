"""Unit-тесты SQL-подобной консоли запросов (Фаза 11, E1): query.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
from onec_converter.query import QueryError, parse_where, query_table_sql
from onec_converter.source_8x_file import Database1CD


def _fields() -> list[FixtureField]:
    return [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
        FixtureField('_QUANTITY', 'N', length=12, precision=2),
        FixtureField('_DATE', 'DT'),
    ]


def _rows() -> list[bytes]:
    rows = []
    for i, (code, descr, qty, marked) in enumerate([
        ('000000001', 'Яблоки', 10.5, False),
        ('000000002', 'Груши зелёные', 3.25, False),
        ('000000003', 'Яблоки красные', 7, True),
    ]):
        rows.append(encode_row(_fields(), {
            '_CODE': code, '_DESCRIPTION': descr, '_QUANTITY': qty,
            '_MARKED': marked,
        }))
    return rows


@pytest.fixture
def db(tmp_path: Path) -> Database1CD:
    data = build_fake_1cd([FixtureTable('_REFERENCE42', fields=_fields(),
                                        rows=_rows())])
    p = tmp_path / 'base.1CD'
    p.write_bytes(data)
    return Database1CD(p)


def test_select_all(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42', limit=100)
    assert len(rows) == 3
    assert rows[0]['_CODE'] == '000000001'
    assert rows[0]['_DESCRIPTION'] == 'Яблоки'


def test_select_projection(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42', select='_CODE,_QUANTITY',
                           limit=100)
    assert rows[0] == {'_CODE': '000000001', '_QUANTITY': 10.5}


def test_select_unknown_field(db: Database1CD):
    with pytest.raises(QueryError, match='нет полей'):
        query_table_sql(db, '_REFERENCE42', select='_NOPE')


def test_where_equality_and_number(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42',
                           where='_QUANTITY>5; _MARKED=0', limit=100)
    assert [r['_CODE'] for r in rows] == ['000000001']


def test_where_like(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42',
                           where="_DESCRIPTION LIKE 'Яблоки%'", limit=100)
    assert len(rows) == 2
    assert rows[0]['_CODE'] == '000000001'
    assert rows[1]['_CODE'] == '000000003'


def test_where_like_middle(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42',
                           where="_DESCRIPTION LIKE '%зелёные%'", limit=100)
    assert [r['_CODE'] for r in rows] == ['000000002']


def test_order_by_desc(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42', order_by='_QUANTITY DESC',
                           limit=100)
    assert [r['_CODE'] for r in rows] == ['000000001', '000000003', '000000002']


def test_limit(db: Database1CD):
    rows = query_table_sql(db, '_REFERENCE42', limit=2)
    assert len(rows) == 2
    with pytest.raises(QueryError, match='limit'):
        query_table_sql(db, '_REFERENCE42', limit=0)


def test_missing_table(db: Database1CD):
    with pytest.raises(QueryError, match='таблица не найдена'):
        query_table_sql(db, '_NOPE')


def test_bad_where(db: Database1CD):
    with pytest.raises(QueryError, match='не разобрано'):
        query_table_sql(db, '_REFERENCE42', where='???')


def test_parse_where_ops():
    conds = parse_where('a>=1; b!=2; c LIKE \'x%\'')
    assert [(c.field, c.op) for c in conds] == [('a', '>='), ('b', '!='),
                                                ('c', 'like')]


def test_ref_field_decodes_to_guid_name(tmp_path: Path):
    """REF (тип R) — {guid, name}; 'B' (16 байт) — строка GUID."""
    from onec_converter.query import decode_value
    from onec_converter.source_8x_file import FieldDef

    class _FakeRef:
        def ref_name(self, table: str, raw16: bytes) -> str | None:
            return 'Номенклатура' if raw16 != b'\x00' * 16 else None

    fdef = FieldDef('_REF', 'R', False, 16, 0, True, 1, 16)
    raw = bytes.fromhex('11111111222233334444555566667777')
    val = decode_value(_FakeRef(), 'T', fdef, raw)  # type: ignore[arg-type]
    assert val == {'guid': '11111111-2222-3333-4444-555566667777',
                   'name': 'Номенклатура'}
    assert decode_value(_FakeRef(), 'T', fdef, b'\x00' * 16) is None  # type: ignore[arg-type]
