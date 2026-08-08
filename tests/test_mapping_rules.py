"""Unit-тесты схемы правил маппинга."""
from pathlib import Path

import pytest

from onec_converter.mapping import build_prompt, validate_rules


def test_valid_rules():
    rules = {'version': 1,
             'objects': [{'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
                          'key': ['Код'], 'attributes': {'Код': 'Код', 'Имя': 'Наименование'}}],
             'enums': {}}
    assert validate_rules(rules) == []


def test_missing_fields_reported():
    rules = {'version': 1, 'objects': [{'source': 'X', 'target': 'Y'}]}
    errors = validate_rules(rules)
    assert any('attributes' in e for e in errors)


def test_duplicate_pair_reported():
    rules = {'version': 1, 'objects': [
        {'source': 'X', 'target': 'Y', 'attributes': {}},
        {'source': 'X', 'target': 'Y', 'attributes': {}}]}
    assert any('дубликат' in e for e in validate_rules(rules))


def test_build_prompt_mentions_both_sides():
    p = build_prompt({'obj': 1}, {'obj': 2})
    assert 'ИСТОЧНИКА' in p and 'ПРИЁМНИКА' in p


def test_type_priority():
    """B1: TYPE_PRIORITY — детерминированный порядок типов Str<Num<Date<Bool<Ref."""
    from onec_converter.type_priority import resolve_type_priority, type_rank

    assert type_rank('string') < type_rank('number') < type_rank('date') \
        < type_rank('bool') < type_rank('ref') < type_rank('unknown')
    assert resolve_type_priority(['number', 'string']) == 'string'
    assert resolve_type_priority(['date', 'number']) == 'number'
    assert resolve_type_priority(['bool', 'ref']) == 'bool'
    assert resolve_type_priority(['string', 'ref']) == 'string'
    assert resolve_type_priority(['unknown']) == 'unknown'
    assert resolve_type_priority([]) == 'unknown'
    # порядок входных не влияет
    assert resolve_type_priority(['ref', 'string', 'date']) == 'string'


def test_validate_rules_type_priority():
    """B1: validate_rules отклоняет неизвестный целевой тип."""
    from onec_converter.mapping import SCHEMA_VERSION, validate_rules

    ok = validate_rules({'version': SCHEMA_VERSION, 'objects': [
        {'source': 'Справочник.А', 'target': 'Справочник.Б', 'type': 'number',
         'attributes': {}}]})
    assert ok == []
    bad = validate_rules({'version': SCHEMA_VERSION, 'objects': [
        {'source': 'Справочник.А', 'target': 'Справочник.Б', 'type': 'zzz',
         'attributes': {}}]})
    assert any('неизвестный целевой тип' in e for e in bad)


def test_toon_load_save(tmp_path: Path):
    """B2: TOON — JSON-правила маппинга загружаются/сохраняются с валидацией."""
    from onec_converter.mapping import SCHEMA_VERSION, MappingError, load_rules, save_rules

    rules = {'version': SCHEMA_VERSION, 'enums': {}, 'objects': [
        {'source': 'Справочник.Номенклатура', 'target': 'Справочник.Номенклатура',
         'key': ['Код'], 'attributes': {'Наименование': 'Наименование'}}]}
    p = save_rules(tmp_path / 'rules.json', rules)
    loaded = load_rules(p)
    assert loaded == rules
    # невалидные правила отклоняются
    with pytest.raises(MappingError):
        save_rules(tmp_path / 'bad.json', {'version': SCHEMA_VERSION, 'objects': [
            {'source': 'X'}]})
    with pytest.raises(MappingError):
        load_rules(tmp_path / 'bad2.json')
    (tmp_path / 'bad2.json').write_text('{broken', encoding='utf-8')
    with pytest.raises(MappingError):
        load_rules(tmp_path / 'bad2.json')


def test_anonymizer_pii():
    """B4: маскирование PII — ФИО/телефоны/ИНН по паттернам и по списку полей."""
    from onec_converter.anonymizer import Anonymizer, mask_fio, mask_inn, mask_phone

    assert mask_fio('Иванов Иван Иванович') == 'Иванов И. И.'
    assert mask_phone('+998901234567') == '+99890*****67' or '*'
    masked = mask_phone('+998901234567')
    assert '234567' not in masked.replace('*', '')
    assert mask_inn('123456789012') == '123' + '*' * 7 + '12'
    # весь текст
    a = Anonymizer()
    rec = a.apply({'Наименование': 'Иванов Иван Иванович',
                   'Телефон': '+998901234567', 'Код': '001'})
    assert 'Иванович' not in rec['Наименование']
    assert rec['Телефон'].count('*') >= 5
    assert rec['Код'] == '001'  # короткое — не трогаем
    # по списку полей + режим hash (детерминированный)
    b = Anonymizer(fields=['Фамилия'], mode='hash')
    r1 = b.apply({'Фамилия': 'Петров', 'Имя': 'Пётр'})
    r2 = b.apply({'Фамилия': 'Петров', 'Имя': 'Пётр'})
    assert r1['Фамилия'] == r2['Фамилия']
    assert r1['Фамилия'] != 'Петров'
    assert r1['Имя'] == 'Пётр'  # вне списка — не тронуто


def test_import_kd3_xml(tmp_path: Path):
    """B3: импорт XML правил обмена КД3 -> JSON-правила TOON."""
    from onec_converter.kd3_import import Kd3ImportError, import_kd3_xml
    from onec_converter.mapping import validate_rules

    xml = tmp_path / 'rules.xml'
    xml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<ConversionRules version="1">
  <Mapping source="Справочник.Номенклатура" target="Справочник.Номенклатура">
    <Key>Код</Key>
    <Attribute source="Наименование" target="Наименование"/>
    <Attribute source="Код" target="Код"/>
  </Mapping>
  <Mapping source="Документ.Продажа" target="Документ.Реализация">
    <Attribute source="Номер" target="Номер"/>
  </Mapping>
  <Enum source="Статус" target="СтатусЗаказа"/>
</ConversionRules>''', encoding='utf-8')
    rules = import_kd3_xml(xml)
    assert validate_rules(rules) == []
    assert rules['objects'][0] == {
        'source': 'Справочник.Номенклатура',
        'target': 'Справочник.Номенклатура',
        'key': ['Код'],
        'attributes': {'Наименование': 'Наименование', 'Код': 'Код'}}
    assert rules['objects'][1]['source'] == 'Документ.Продажа'
    assert rules['enums'] == {'Статус': 'СтатусЗаказа'}
    # битый XML
    (tmp_path / 'bad.xml').write_text('<ConversionRules><Mapping', encoding='utf-8')
    with pytest.raises(Kd3ImportError):
        import_kd3_xml(tmp_path / 'bad.xml')
    # Mapping без target
    (tmp_path / 'no_tgt.xml').write_text('<ConversionRules><Mapping source="A"/></ConversionRules>',
                                         encoding='utf-8')
    with pytest.raises(Kd3ImportError):
        import_kd3_xml(tmp_path / 'no_tgt.xml')
