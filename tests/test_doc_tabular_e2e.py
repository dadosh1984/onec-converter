"""e2e: документ с ТЧ переносится мостом (шапка + ТЧ) с обратным тестом."""
from __future__ import annotations

from pathlib import Path

from onec_converter.bridge_export import export_bridge
from onec_converter.bridge_verify import verify_roundtrip
from onec_converter.epf_load import import_bridge
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd

FD = [FixtureField('_IDRREF', 'B', length=16),
      FixtureField('_NUMBER', 'N', length=9),
      FixtureField('_DATE_TIME', 'DT', length=8),
      FixtureField('_POSTED', 'L', length=1)]
FV = [FixtureField('_DOCUMENT1IDRREF', 'B', length=16),
      FixtureField('_KEYFIELD', 'B', length=16),
      FixtureField('_LINENO2', 'N', length=4),
      FixtureField('_FLD3', 'NVC', length=30)]

DOC_META = {'objects': [
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная', 'table': '_DOCUMENT1',
     'attributes': [
         {'name': 'Номер', 'field': '_NUMBER', 'type': 'number',
          'length': 9, 'precision': 0},
         {'name': '_DATE_TIME', 'field': '_DATE_TIME', 'type': 'date',
          'length': 8, 'precision': 0},
     ]},
], 'tables': ['_DOCUMENT1', '_DOCUMENT1_VT2']}


def _mk(tmp, name, rows_doc=(), rows_vt=()):
    p = tmp / name
    p.mkdir(exist_ok=True)
    (p / '1Cv8.1CD').write_bytes(
        write_fake_1cd(tmp / f'{name}.1CD',
                       [FixtureTable('_DOCUMENT1', fields=FD, rows=list(rows_doc)),
                        FixtureTable('_DOCUMENT1_VT2', fields=FV, rows=list(rows_vt))]))
    return p


def test_document_tabular_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr('onec_converter.bridge_export.read_metadata',
                        lambda p: dict(DOC_META))
    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: dict(DOC_META))
    doc_id = bytes.fromhex('02000000110000000000000000000000')
    drow = encode_row(FD, {'_IDRREF': doc_id, '_NUMBER': 1,
                           '_DATE_TIME': '2024-01-15T12:00:00', '_POSTED': 1})
    vrow = encode_row(FV, {'_DOCUMENT1IDRREF': doc_id,
                           '_KEYFIELD': b'\x00' * 16,
                           '_LINENO2': 1, '_FLD3': 'Товар А'})
    src = _mk(tmp_path, 'src', [drow], [vrow])
    tgt = _mk(tmp_path, 'tgt', [encode_row(FD, {})], [encode_row(FV, {})])
    wd = tmp_path / 'wd'

    b_head = tmp_path / 'head.xlsx'
    export_bridge(src, 'Документ.ПриходнаяНакладная', b_head)
    imp = import_bridge(b_head, tgt, workdir=wd / 'head')
    assert imp['ok'] and imp['created'] == 1
    copied = str(Path(imp['copy_path']).parent)
    rep = verify_roundtrip(copied, copied, 'Документ.ПриходнаяНакладная',
                           b_head, workdir=wd / 'vh', key_col='Номер')
    assert rep['ok'], rep

    b_vt = tmp_path / 'vt.xlsx'
    export_bridge(src, 'Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2', b_vt)
    imp2 = import_bridge(b_vt, copied, workdir=wd / 'vt')
    assert imp2['ok']
    copied2 = str(Path(imp2['copy_path']).parent)
    rep2 = verify_roundtrip(copied2, copied2,
                            'Документ.ПриходнаяНакладная.ТЧ._DOCUMENT1_VT2',
                            b_vt, workdir=wd / 'vv', key_col='Номер')
    assert rep2['ok'], rep2
