"""Классификация объектов ИБ: user/formula/service по типу 1С."""
from __future__ import annotations

from onec_converter.classify import build_plan, classify_objects

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты'},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная'},
    {'kind': 'Константа', 'name': 'Организация'},
    {'kind': 'РегистрСведений', 'name': 'Цены'},
    {'kind': 'Отчет', 'name': 'ОСВ'},
    {'kind': 'Обработка', 'name': 'ЗакрытиеМесяца'},
    {'kind': 'РегистрНакопления', 'name': 'Остатки'},
    {'kind': 'РегистрБухгалтерии', 'name': 'Хозрасчетный'},
    {'kind': 'ПланСчетов', 'name': 'Основной'},
    {'kind': 'Перечисление', 'name': 'ВидыКонтрагентов'},
    {'kind': 'ОбщийМодуль', 'name': 'РаботаСФормами'},
]}


def test_catalogs_documents_constants_are_user():
    r = classify_objects(META)
    assert r['Справочник.Контрагенты'] == 'user'
    assert r['Документ.ПриходнаяНакладная'] == 'user'
    assert r['Константа.Организация'] == 'user'
    assert r['РегистрСведений.Цены'] == 'user'


def test_reports_registers_result_are_formula():
    r = classify_objects(META)
    assert r['Отчет.ОСВ'] == 'formula'
    assert r['Обработка.ЗакрытиеМесяца'] == 'formula'
    assert r['РегистрНакопления.Остатки'] == 'formula'
    assert r['РегистрБухгалтерии.Хозрасчетный'] == 'formula'


def test_service_objects():
    r = classify_objects(META)
    assert r['ПланСчетов.Основной'] == 'service'
    assert r['Перечисление.ВидыКонтрагентов'] == 'service'
    assert r['ОбщийМодуль.РаботаСФормами'] == 'service'


PLAN_META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты'},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная'},
    {'kind': 'Отчет', 'name': 'ОСВ'},
]}


def test_plan_contains_only_user_objects():
    plan = build_plan(PLAN_META)
    names = [p['name'] for p in plan]
    assert 'Справочник.Контрагенты' in names
    # Документ — user, но мост его пока не выгружает (только Справочник/РегистрСведений)
    assert 'Документ.ПриходнаяНакладная' not in names
    assert 'Отчет.ОСВ' not in names


def test_plan_has_file_names():
    plan = build_plan(PLAN_META)
    assert all(p['file'].endswith('.xlsx') for p in plan)
    assert plan[0]['file'] == 'Справочник.Контрагенты.xlsx'
