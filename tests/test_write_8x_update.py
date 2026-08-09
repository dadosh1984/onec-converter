"""RED-тесты перезаписи существующей строки по _IDRREF (write_8x.update_record)."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import WriteError, update_record

IDR = bytes.fromhex('02000000110000000000000000000000')
IDR2 = bytes.fromhex('02000000220000000000000000000000')

FIELDS = [
    FixtureField('_IDRREF', 'RV', length=16),
    FixtureField('_VERSION', 'I', length=8),
    FixtureField('_MARKED', 'L', length=1),
    FixtureField('_ISMETADATA', 'L', length=1),
    FixtureField('_CODE', 'NVC', length=9, null_exists=True),
    FixtureField('_DESCRIPTION', 'NVC', length=50, null_exists=True),
]


def _base(tmp_path: Path) -> Path:
    rows = [
        encode_row(FIELDS, {'_IDRREF': IDR, '_CODE': '00001', '_DESCRIPTION': 'ООО Ромашка'}),
        encode_row(FIELDS, {'_IDRREF': IDR2, '_CODE': '00002', '_DESCRIPTION': 'ООО Поле'}),
    ]
    t = FixtureTable('_Reference77', fields=FIELDS, rows=rows)
    path = tmp_path / '1Cv8.1CD'
    write_fake_1cd(path, [t])
    return path


def _read_all(path: Path) -> list[dict[str, str]]:
    with Database1CD(path) as db:
        t = db.tables['_Reference77']
        out = []
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            out.append({'id': row[t.fields['_IDRREF'].offset:t.fields['_IDRREF'].offset + 16].hex(),
                        'code': _nvc(row, t, '_CODE'),
                        'descr': _nvc(row, t, '_DESCRIPTION')})
        return out


def _nvc(row: bytes, t: object, name: str) -> str:
    fd = t.fields[name]
    from onec_converter.source_8x_file import decode_nvc
    return decode_nvc(row[fd.offset:fd.offset + fd.size], fd.null_exists) or ''


def test_update_existing_record(tmp_path: Path):
    path = _base(tmp_path)
    # новая строка с тем же _IDRREF, но другим кодом/наименованием
    new_row = encode_row(FIELDS, {'_IDRREF': IDR, '_CODE': '00001',
                                  '_DESCRIPTION': 'ООО Ромашка (обновлено)'})
    ok = update_record(path, '_Reference77', IDR, new_row)
    assert ok is True
    recs = _read_all(path)
    assert len(recs) == 2
    assert recs[0]['descr'] == 'ООО Ромашка (обновлено)'
    assert recs[1]['descr'] == 'ООО Поле'  # вторая строка не тронута


def test_update_missing_idref_returns_false(tmp_path: Path):
    path = _base(tmp_path)
    new_row = encode_row(FIELDS, {'_IDRREF': b'\x09' * 16, '_CODE': 'X'})
    ok = update_record(path, '_Reference77', b'\x09' * 16, new_row)
    assert ok is False
    assert len(_read_all(path)) == 2  # ничего не добавлено


def test_update_wrong_row_length_raises(tmp_path: Path):
    path = _base(tmp_path)
    with pytest.raises(WriteError):
        update_record(path, '_Reference77', IDR, b'\x00' * 10)


def test_update_unknown_table_raises(tmp_path: Path):
    path = _base(tmp_path)
    with pytest.raises(WriteError):
        update_record(path, '_NoSuchTable', IDR, b'\x00' * 100)
