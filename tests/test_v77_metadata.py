"""Unit-тесты v77_metadata (на моке olefile) + интеграция на реальной базе."""
from pathlib import Path

import pytest

from onec_converter.v77_metadata import V77Metadata, MetadataError


def test_missing_md_raises(tmp_path: Path):
    with pytest.raises(MetadataError):
        V77Metadata(tmp_path / 'nope.MD')


REAL_BASE = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1С_7.7')


@pytest.mark.integration
def test_real_base_metadata():
    if not (REAL_BASE / '1Cv7.MD').is_file():
        pytest.skip('реальная база 7.7 недоступна')
    md = V77Metadata(REAL_BASE / '1Cv7.MD')
    try:
        tops = md.top_storages()
        assert 'Container.Contents' in tops
        assert 'Metadata' in tops
        objs = md.object_storages()
        assert len(objs) > 0
    finally:
        md.close()
