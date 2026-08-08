"""Юнит-тесты парсера 1Cv8.1CD на синтетическом файле (tests/fixtures/gen_1cd.py)."""

from __future__ import annotations

import struct
import zlib
from datetime import datetime
from pathlib import Path

import pytest

from onec_converter.source_8x_file import (
    Database1CD,
    FormatError,
    bin_to_guid,
    decode_datetime,
    decode_field,
    decode_nc,
    decode_numeric,
    decode_nvc,
    parse_bracket,
    read_dbschema,
    read_metadata,
    read_table,
    to_model,
)
from tests.fixtures.gen_1cd import (
    FixtureField,
    FixtureTable,
    build_1cd,
    enc_datetime,
    encode_row,
)

CATALOG_GUID = 'cf4abea6-37b2-11d4-940f-008048da11f9'
OBJ_GUID = '8496674d-1111-2222-3333-444455556666'
MAIN_GUID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def ref_fields() -> list[FixtureField]:
    return [
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_VERSION', 'RV'),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=5),
        FixtureField('_DESCRIPTION', 'NVC', length=20),
        FixtureField('_FLD174', 'NVC', length=9, null_exists=True),
        FixtureField('_N', 'N', length=6, precision=2),
        FixtureField('_DT', 'DT'),
    ]


def ref_rows() -> list[bytes]:
    f = ref_fields()
    return [
        encode_row(f, {
            '_IDRREF': bytes.fromhex('0102030405060708090a0b0c0d0e0f10'),
            '_VERSION': bytes.fromhex('11' * 16),
            '_MARKED': False, '_CODE': '00001', '_DESCRIPTION': 'Тест один',
            '_FLD174': None, '_N': 1234.5, '_DT': '20240115093045',
        }),
        encode_row(f, {
            '_IDRREF': bytes.fromhex('0102030405060708090a0b0c0d0e0f11'),
            '_VERSION': bytes.fromhex('11' * 16),
            '_MARKED': True, '_CODE': '00002', '_DESCRIPTION': 'Тест два',
            '_FLD174': '111111111', '_N': -1, '_DT': None,
        }),
    ]


def write_ref1cd(tmp_path: Path, tables: list[FixtureTable]) -> Path:
    p = tmp_path / 'base.1cd'
    p.write_bytes(build_1cd(tables))
    return p


# ---------------------------------------------------------------------------
# Заголовок и каталог таблиц
# ---------------------------------------------------------------------------


def test_header_and_catalog(tmp_path: Path):
    t = FixtureTable('_REFERENCE3', fields=ref_fields(), rows=ref_rows())
    p = write_ref1cd(tmp_path, [t])
    with Database1CD(p) as db:
        assert str(db.version) == '8.3.8.0'
        assert db.page_size == 8192
        assert db.total_pages > 0
        assert db.locale == 'ru_RU'
        assert set(db.tables) == {'_REFERENCE3'}
        td = db.tables['_REFERENCE3']
        assert td.row_length > 5
        # RV — всегда offset 1, _IDRREF следом
        assert td.fields['_VERSION'].offset == 1
        assert td.fields['_IDRREF'].offset == 17
        assert td.data_page > 0


def test_both_table_name_styles(tmp_path: Path):
    """8.1-эпоха (_REFERENCE3) и 8.3-стиль (_Reference74)."""
    t1 = FixtureTable('_REFERENCE3', fields=ref_fields(), rows=ref_rows())
    t2 = FixtureTable('_Reference74', fields=ref_fields(), rows=ref_rows())
    p = write_ref1cd(tmp_path, [t1, t2])
    with Database1CD(p) as db:
        assert '_REFERENCE3' in db.tables
        assert '_Reference74' in db.tables


def test_multi_chunk_description(tmp_path: Path):
    """Описание таблицы длиннее 250 б — цепочка blob-чанков каталога."""
    many = [FixtureField(f'_FLD{i:03d}', 'NVC', length=30) for i in range(30)]
    t = FixtureTable('_BIGTABLE', fields=many,
                     rows=[encode_row(many, {f'_FLD{i:03d}': f'значение {i}' for i in range(30)})])
    p = write_ref1cd(tmp_path, [t])
    with Database1CD(p) as db:
        td = db.tables['_BIGTABLE']
        assert len(td.fields) == 30


def test_not_1cd_raises(tmp_path: Path):
    p = tmp_path / 'bad.1cd'
    p.write_bytes(b'garbage' * 10)
    with pytest.raises(FormatError):
        Database1CD(p)


# ---------------------------------------------------------------------------
# Строки и типы
# ---------------------------------------------------------------------------


def test_row_decoding(tmp_path: Path):
    t = FixtureTable('_REFERENCE3', fields=ref_fields(), rows=ref_rows())
    p = write_ref1cd(tmp_path, [t])
    with Database1CD(p) as db:
        rows = list(db.table_rows(db.tables['_REFERENCE3']))
        assert len(rows) == 2
        f = db.tables['_REFERENCE3'].fields
        r0 = decode_field(f['_IDRREF'], rows[0][f['_IDRREF'].offset:][:16])
        assert r0 == '01020304-0506-0708-090a-0b0c0d0e0f10'
        assert decode_field(f['_DESCRIPTION'], rows[0][f['_DESCRIPTION'].offset:][:f['_DESCRIPTION'].size]) == 'Тест один'
        # null_exists NVC
        assert decode_field(f['_FLD174'], rows[0][f['_FLD174'].offset:][:f['_FLD174'].size]) is None
        assert decode_field(f['_FLD174'], rows[1][f['_FLD174'].offset:][:f['_FLD174'].size]) == '111111111'
        # число и дата
        assert decode_field(f['_N'], rows[0][f['_N'].offset:][:4]) == 1234.5
        assert decode_field(f['_N'], rows[1][f['_N'].offset:][:4]) == -1
        assert decode_field(f['_DT'], rows[0][f['_DT'].offset:][:7]) == datetime(2024, 1, 15, 9, 30, 45)
        assert decode_field(f['_DT'], rows[1][f['_DT'].offset:][:7]) is None
        assert decode_field(f['_MARKED'], rows[1][f['_MARKED'].offset:][:1]) == 1


def test_read_table_iterator(tmp_path: Path):
    t = FixtureTable('_REFERENCE3', fields=ref_fields(), rows=ref_rows())
    p = write_ref1cd(tmp_path, [t])
    rows = list(read_table(p, '_REFERENCE3'))
    assert len(rows) == 2
    assert rows[0]['_CODE'] == '00001'
    assert rows[1]['_MARKED'] == 1


def test_decode_helpers():
    assert decode_nvc(struct.pack('<H', 3) + 'абв'.encode('utf-16-le')) == 'абв'
    assert decode_nvc(b'\x00' + struct.pack('<H', 3) + 'абв'.encode('utf-16-le'), True) is None
    assert decode_nvc(b'\x01' + struct.pack('<H', 3) + 'абв'.encode('utf-16-le'), True) == 'абв'
    assert decode_nc('CODE'.encode('utf-16-le') + b'\x20\x00' * 5) == 'CODE'
    assert decode_numeric(bytes.fromhex('10002000'), 6, 2) == 2.0
    assert decode_numeric(bytes.fromhex('00000020'), 6, 0) == -2
    assert decode_datetime(enc_datetime('20240115093045')) == datetime(2024, 1, 15, 9, 30, 45)
    assert decode_datetime(b'\x00' * 7) is None
    assert bin_to_guid(bytes.fromhex('0102030405060708090a0b0c0d0e0f10')) == \
        '01020304-0506-0708-090a-0b0c0d0e0f10'


# ---------------------------------------------------------------------------
# Blob-цепочки (BINARYDATA, DBSCHEMA)
# ---------------------------------------------------------------------------


def test_blob_chain(tmp_path: Path):
    """Blob длиннее 250 б — цепочка чанков через nxt."""
    payload = b'PAYLOAD-' * 60  # 480 байт
    chunk3 = (0, payload[240:480])
    chunk1 = (3, b'')  # ждём: read_blob стартует с chunk 1
    # read_blob стартует с first_chunk и идёт по nxt
    # => chain: chunk1 -> chunk3
    chunk1 = (3, b'first')
    t = FixtureTable('_DOCS', fields=[
        FixtureField('_NUMBER', 'NC', length=10),
    ], blobs={1: chunk1, 3: chunk3})
    # BINARYDATA-подобный blob в _DOCS не нужен — просто проверяем read_blob
    p = write_ref1cd(tmp_path, [t])
    with Database1CD(p) as db:
        td = db.tables['_DOCS']
        assert db.read_blob(td, 1, 11) == b'first' + payload[240:246]


def test_read_dbschema(tmp_path: Path):
    schema_text = '\ufeff{"ReferenceN","N",0,"",{"Fld174","NVC"}}'
    blob = schema_text.encode('utf-8-sig')
    t = FixtureTable('DBSCHEMA', fields=[
        FixtureField('SERIALIZEDDATA', 'I'),
    ], blobs={1: (0, b'')})
    t.blobs[1] = (0, blob) if len(blob) <= 250 else {1: (2, blob[:240]), 2: (0, blob[240:])}[1]
    if len(blob) > 250:
        t.blobs = {1: (2, blob[:240]), 2: (0, blob[240:])}
    row = b'\x00' + struct.pack('<2I', 1, len(blob))
    t.rows = [row]
    p = write_ref1cd(tmp_path, [t])
    text = read_dbschema(p)
    assert 'ReferenceN' in text


# ---------------------------------------------------------------------------
# Конфигурация: CONFIG/PARAMS/DBNames и привязка таблица↔объект
# ---------------------------------------------------------------------------


def _config_tables() -> list[FixtureTable]:
    """root + объект «Банки» + PARAMS(DBNames) + справочник _REFERENCE3."""
    root_text = f"{{2,{MAIN_GUID},x}}"
    main_text = f"{{1,{{47,{{{CATALOG_GUID},1,{OBJ_GUID}}}}}}}"
    q = '"'
    obj_text = ('{1,{47,{0,{0,{0,0,' + OBJ_GUID + '},' + q + 'Банки' + q + ','
               + '{1,' + q + 'ru' + q + ',' + q + 'Банки и МФО' + q + '},' + q + q + '}}}}')
    dbnames_text = '{5029,{1,{' + f'{{{OBJ_GUID},"Reference",3}}' + '}}'

    def blob_chain(data: bytes, first: int = 1) -> dict[int, tuple[int, bytes]]:
        if len(data) <= 250:
            return {first: (0, data)}
        return {first: (first + 1, data[:240]), first + 1: (0, data[240:])}

    config = FixtureTable('CONFIG', fields=[
        FixtureField('FILENAME', 'NVC', length=128),
        FixtureField('CREATION', 'DT'),
        FixtureField('MODIFIED', 'DT'),
        FixtureField('ATTRIBUTES', 'N', length=5),
        FixtureField('BINARYDATA', 'I'),
    ])
    config.rows = []
    for i, (name, text) in enumerate([
        ('root', root_text), (MAIN_GUID, main_text), (OBJ_GUID, obj_text),
    ]):
        data = zlib.compress(text.encode('utf-8'), 9)[2:-4]  # raw deflate
        config.blobs.update(blob_chain(data, first=1 + i * 10))
        config.rows.append(encode_row(config.fields, {
            'FILENAME': name, 'CREATION': None, 'MODIFIED': None,
            'ATTRIBUTES': 1, 'BINARYDATA': (1 + i * 10, len(data)),
        }))

    params = FixtureTable('PARAMS', fields=[
        FixtureField('FILENAME', 'NVC', length=128),
        FixtureField('CREATION', 'DT'),
        FixtureField('MODIFIED', 'DT'),
        FixtureField('ATTRIBUTES', 'N', length=5),
        FixtureField('DATASIZE', 'N', length=10),
        FixtureField('BINARYDATA', 'I'),
    ])
    dbnames = zlib.compress(dbnames_text.encode('utf-8-sig'), 9)[2:-4]
    params.blobs = blob_chain(dbnames, first=1)
    params.rows = [encode_row(params.fields, {
        'FILENAME': 'DBNames', 'CREATION': None, 'MODIFIED': None,
        'ATTRIBUTES': 1, 'DATASIZE': len(dbnames), 'BINARYDATA': (1, len(dbnames)),
    })]

    ref = FixtureTable('_REFERENCE3', fields=ref_fields(), rows=ref_rows())
    return [config, params, ref]


def test_read_dbnames(tmp_path: Path):
    p = write_ref1cd(tmp_path, _config_tables())
    with Database1CD(p) as db:
        dn = db.read_dbnames()
        assert dn[OBJ_GUID] == ('Reference', 3)


def test_read_metadata_binding(tmp_path: Path):
    p = write_ref1cd(tmp_path, _config_tables())
    md = read_metadata(p)
    objs = [o for o in md['objects'] if o['name'] == 'Банки']
    assert len(objs) == 1
    o = objs[0]
    assert o['kind'] == 'Справочник'
    assert o['table'] == '_REFERENCE3'
    assert o['ref_num'] == 3
    assert o['synonym'] == 'Банки и МФО'
    # системные имена полей
    names = {a['name'] for a in o['attributes']}
    assert 'Код' in names and 'Наименование' in names


def test_to_model(tmp_path: Path):
    """read_metadata -> единая модель model.py (ObjectType/AttrDef)."""
    p = write_ref1cd(tmp_path, _config_tables())
    objs = to_model(p)
    banks = [o for o in objs if o.name == 'Банки']
    assert len(banks) == 1
    o = banks[0]
    assert o.kind == 'Справочник'
    assert o.synonym == 'Банки и МФО'
    assert o.full_name == 'Справочник.Банки'
    names = {a.name: a for a in o.attributes}
    assert names['Код'].type.kind == 'string'
    assert names['Наименование'].type.kind == 'string'


def test_parse_bracket():
    tree = parse_bracket('{a,"строка с ""кавычкой""",{1,2},""}')
    assert tree[0] == 'a'
    assert tree[1] == 'строка с "кавычкой"'
    assert tree[2] == ['1', '2']
    assert tree[3] == ''
    assert parse_bracket('\ufeff{1}') == ['1']
