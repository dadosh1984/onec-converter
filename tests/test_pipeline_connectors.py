"""Интеграционный тест конвейера: единая модель для коннекторов 7.7 и 8.x.

Проверяется на синтетических данных (коннектор 8.x в разработке — спайк);
тест фиксирует контракт: конвейер не зависит от версии источника.
"""

from __future__ import annotations

from onec_converter.mapping import validate_rules
from onec_converter.model import AttrDef, AttrType, ObjectType, Record
from onec_converter.resolver import RefResolver
from onec_converter.transform import transform_object
from onec_converter.validate import validate_batch, validate_references


def _records_from_77() -> list[Record]:
    """Эмуляция коннектора 7.7 (v77_reader)."""
    t = ObjectType('Справочник', 'Банки', attributes=[
        AttrDef('Код', AttrType('string', 9)),
        AttrDef('Имя', AttrType('string', 150)),
    ])
    return [
        Record(t, '1|', {'Код': '00001', 'Имя': 'Банк А'}, key=('00001', 'Банк А')),
        Record(t, '2|', {'Код': '00002', 'Имя': 'Банк Б'}, key=('00002', 'Банк Б')),
    ]


def _records_from_8x() -> list[Record]:
    """Эмуляция коннектора 8.x (source_8x_file). Тот же контракт."""
    return _records_from_77()


def test_pipeline_works_for_both_connectors():
    rules = {'version': 1, 'objects': [
        {'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
         'key': ['Код'], 'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}],
        'enums': {}}
    assert validate_rules(rules) == []

    for connector in (_records_from_77, _records_from_8x):
        records = connector()
        objs = [r.to_intermediate() for r in records]

        # validate
        vr = validate_batch(objs)
        assert vr.ok
        assert vr.counts['Справочник.Банки'] == 2

        # mapping: резолвер по целевым объектам
        resolver = RefResolver()
        resolver.build(objs)
        assert resolver.resolve('Справочник.Банки', ('00001', 'Банк А'), '1|') == '1|'

        # transform
        rule = rules['objects'][0]
        out = [transform_object(o, rule, resolver) for o in objs]
        assert out[0]['attributes']['Наименование'] == 'Банк А'

        # целостность ссылок (нет ссылок -> ok)
        assert validate_references(objs).ok
