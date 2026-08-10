"""План переноса: только user-разделы, каждый в отдельный файл."""
from __future__ import annotations

from onec_converter.classify import build_plan

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Контрагенты'},
    {'kind': 'Документ', 'name': 'ПриходнаяНакладная'},
    {'kind': 'Отчет', 'name': 'ОСВ'},
]}


def test_plan_contains_only_user_objects():
    plan = build_plan(META)
    names = [p['name'] for p in plan]
    assert 'Справочник.Контрагенты' in names
    assert 'Документ.ПриходнаяНакладная' in names
    assert 'Отчет.ОСВ' not in names


def test_plan_has_file_names():
    plan = build_plan(META)
    assert all(p['file'].endswith('.xlsx') for p in plan)
    assert plan[0]['file'] == 'Справочник.Контрагенты.xlsx'
