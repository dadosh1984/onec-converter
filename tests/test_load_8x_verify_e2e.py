"""e2e Фаза 16: verify после записи на КОПИИ реальной базы 8.1."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # реальные 2.5ГБ базы — вне coverage-замера (Фаза 50)

from onec_converter.load_8x import load_direct
from onec_converter.write_8x import copy_1cd

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует')


@REQUIRED
@pytest.mark.integration
def test_verify_after_load_direct_real_base(tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch):
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    (tgt / '1Cv8.1CD').write_bytes(copy_1cd(BASE_81, tmp_path / 'c.1CD').read_bytes())
    meta = {'objects': [
        {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE3',
         'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                         'length': 9, 'precision': 0},
                        {'name': 'Наименование', 'field': '_DESCRIPTION',
                         'type': 'NVC', 'length': 40, 'precision': 0}]},
    ]}
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: meta)
    objs = [
        {'type': 'Справочник.Банки', 'key': ['00002', 'Банки РУз'],
         'attributes': {'Код': '00002', 'Наименование': 'Банки РУз'},
         'references': {}},
    ]
    rep = load_direct(tgt, objs, workdir=tmp_path / 'wd')
    assert rep['ok'] is True
    v = rep.get('verify') or {}
    assert v.get('ok') is True, v
    assert v.get('checked') == 1
