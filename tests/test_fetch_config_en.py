"""fetch-config: английские теги MDClasses (Catalog/Document/Constant...)."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from onec_converter.fetch_config import _META_TAGS_EN


def test_mapping_has_key_catalogs():
    assert _META_TAGS_EN['Catalog'] == 'Справочник'
    assert _META_TAGS_EN['Document'] == 'Документ'
    assert _META_TAGS_EN['Constant'] == 'Константа'
    assert _META_TAGS_EN['Enum'] == 'Перечисление'
    assert _META_TAGS_EN['AccumulationRegister'] == 'РегистрНакопления'
    assert _META_TAGS_EN['InformationRegister'] == 'РегистрСведений'
    assert _META_TAGS_EN['ChartOfAccounts'] == 'ПланСчетов'


def test_mapping_values_are_valid_xml_tags():
    # русские значения — это теги из _META_TAGS (совместимость с русской выгрузкой)
    from onec_converter.fetch_config import _META_TAGS
    for ru in _META_TAGS_EN.values():
        assert ru in _META_TAGS
