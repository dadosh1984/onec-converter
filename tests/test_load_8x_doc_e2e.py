"""e2e Фаза 15: load_direct реального документа со ссылкой и ТЧ на КОПИИ 8.1.

Оригинал не изменяется (пишем в tmp-копию). REF-поле документа резолвится
в _IDRREF _REFERENCE3 по ключу '00002|Банки РУз'; VT-строка привязывается
к базовой строке (_DOCUMENT41_IDRREF).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # реальные 2.5ГБ базы — вне coverage-замера (Фаза 50)

from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD, decode_nc, decode_numeric

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует')


@REQUIRED
@pytest.mark.integration
def test_load_direct_document_with_ref_and_vt(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch):
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    from onec_converter.write_8x import copy_1cd
    cp = copy_1cd(BASE_81, tmp_path / 'origcopy.1CD')
    (tgt / '1Cv8.1CD').write_bytes(cp.read_bytes())

    meta = {'objects': [
        {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE3',
         'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                         'length': 9, 'precision': 0}]},
        {'kind': 'Документ', 'name': 'Платёжка', 'table': '_DOCUMENT41',
         'attributes': [{'name': 'Номер', 'field': '_NUMBER', 'type': 'N',
                         'length': 8, 'precision': 0},
                        {'name': '_FLD762', 'field': '_FLD762RREF',
                         'type': 'ref', 'length': 16, 'precision': 0}]},
    ]}
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: meta)
    obj = {
        'type': 'Документ.Платёжка', 'key': [1],
        'attributes': {'Номер': 1},
        'references': {'_FLD762': 'Справочник.Банки:00002|Банки РУз'},
        'tab_sections': {'Строки': {'rows': [
            {'_FLD773': 100.0, '_FLD774': 1.0},
        ]}},
    }
    rep = load_direct(tgt, [obj], workdir=tmp_path / 'wd')
    assert rep['ok'] is True, rep
    with Database1CD(Path(rep['copy_path'])) as db:
        # REF-поле документа = _IDRREF строки '00002' справочника
        bank = db.tables['_REFERENCE3']
        bank_idref = None
        code = bank.fields['_CODE']
        for row in db.table_rows(bank):
            if decode_nc(row[code.offset:code.offset + code.size]) == '00002':
                idf = bank.fields['_IDRREF']
                bank_idref = row[idf.offset:idf.offset + 16]
                break
        assert bank_idref is not None
        doc = db.tables['_DOCUMENT41']
        doc_rows = list(db.table_rows(doc))
        last = doc_rows[-1]
        rf = doc.fields['_FLD762RREF']
        assert last[rf.offset:rf.offset + 16] == bank_idref
        # VT-строка привязана к базовой строке
        vt = db.tables['_DOCUMENT41_VT770']
        vrows = list(db.table_rows(vt))
        new = vrows[-1]
        pf = vt.fields['_DOCUMENT41_IDRREF']
        lf = vt.fields['_LINENO771']
        qf = vt.fields['_FLD773']
        # parent-ссылка VT на записанную базовую строку (её idref не нулевой)
        assert new[pf.offset:pf.offset + 16] != b'\x00' * 16
        assert decode_numeric(new[lf.offset:lf.offset + lf.size],
                              lf.length, 0) == 1  # первая строка ТЧ
        assert decode_numeric(new[qf.offset:qf.offset + qf.size],
                              qf.length, qf.precision) == 100.0
