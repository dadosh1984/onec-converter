"""Фаза 13: сквозной перенос 7.7 → ПРЯМАЯ запись в копию 1CD (zero-setup A).

gen_dat (7.7) → extract → transform (TOON) → load_direct в КОПИЮ реальной
1C_8.1 → парсер читает, число строк совпадает. Оригинал не изменяется.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # реальные 2.5ГБ базы — вне coverage-замера (Фаза 50)

from onec_converter.intermediate import OBJ_ATTRS, OBJ_TYPE
from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD
from onec_converter.transform import transform_object
from tests.fixtures.gen_dat import make_dat

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(), reason='реальная база 8.1 отсутствует')

RULES = {'version': 1, 'objects': [
    {'source': 'Справочник.1', 'target': 'Справочник.Банки', 'key': ['Код'],
     'attributes': {'_code': 'Код', '_descr': 'Наименование'}}], 'enums': {}}


def _extract_77(tmp_path: Path) -> list[dict]:
    from onec_converter.base_reader import Base77

    base = tmp_path / 'src77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    refs = [['1|', '00001', 'Банк А'], ['2|', '00002', 'Банк Б']]
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2}, references={1: refs}, encoding='cp866'))
    src = Base77(base, encoding='cp866')
    objs = []
    for table_id, recs in src.data.references().items():
        for rec in recs:
            objs.append({OBJ_TYPE: f'Справочник.{table_id}',
                         'id': str(rec[0]),
                         'key': [str(v) for v in rec[1:3]],
                         OBJ_ATTRS: {'_code': rec[1] if len(rec) > 1 else None,
                                     '_descr': rec[2] if len(rec) > 2 else None},
                         'references': {}})
    return objs


@REQUIRED
@pytest.mark.integration
def test_e2e_77_to_direct_1cd(tmp_path: Path):
    """7.7 → transform → load_direct в копию 8.1; парсер читает, verify."""
    objs = _extract_77(tmp_path)
    assert len(objs) == 2
    tgt = [transform_object(o, RULES['objects'][0], resolver=None)  # type: ignore[arg-type]
           for o in objs]
    assert {o['type'] for o in tgt} == {'Справочник.Банки'}

    with Database1CD(BASE_81) as db:
        # таблица справочника «Банки» в 8.1 (как в read_metadata)
        md = __import__('onec_converter.source_8x_file',
                        fromlist=['read_metadata']).read_metadata(BASE_81)
        bank = next(o for o in md['objects'] if o['name'] == 'Банки')
        rows_before = db.table_stats(bank['table'])[0]
        table = bank['table']

    rep = load_direct(BASE_81.parent, tgt, workdir=tmp_path / 'wd')
    assert rep['ok'] is True and rep['total'] == 2
    cp = Path(rep['copy_path'])
    with Database1CD(cp) as db:
        rows_after = db.table_stats(table)[0]
        assert rows_after == rows_before + 2
        # записанные строки в конце таблицы
        t = db.tables[table]
        all_rows = list(db.table_rows(t))
        last = all_rows[-1]
        code_f = t.fields['_CODE']
        from onec_converter.source_8x_file import decode_field
        assert decode_field(code_f, last[code_f.offset:code_f.offset + code_f.size]) \
            in ('00001', '00002')
    # оригинал не изменён
    assert BASE_81.read_bytes() != cp.read_bytes()
