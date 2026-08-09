"""Тесты CLI extract: 7.7/8.x -> intermediate JSON (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter.cli import main
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd
from tests.fixtures.gen_dat import make_dat


def _base77(tmp_path: Path) -> Path:
    base = tmp_path / 'base77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    return base


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def test_extract_77(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out)])
    assert rc == 0
    objs = _load(out)
    assert len(objs) == 2
    assert objs[0]['type'] == 'Справочник.1'
    assert objs[0]['key'] == ['0001', 'Товар А']
    assert objs[0]['attributes']['_descr'] == 'Товар А'


def test_extract_limit(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--limit', '1'])
    assert rc == 0
    assert len(_load(out)) == 1


def test_extract_objects_filter(tmp_path: Path):
    base = tmp_path / 'base77m'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2, 2: 1},
        references={1: [['1|', '0001', 'Товар А']],
                    2: [['1|', '0001', 'Контрагент X']]}))
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--objects', 'Справочник.2'])
    assert rc == 0
    objs = _load(out)
    assert len(objs) == 1
    assert objs[0]['type'] == 'Справочник.2'


def test_extract_anonymize(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--anonymize-fields', '_descr'])
    assert rc == 0
    objs = _load(out)
    # 'Товар А' не содержит PII — остаётся; маскируется ФИО/телефон/ИНН
    assert objs[0]['attributes']['_descr'] == 'Товар А'


def test_extract_anonymize_fio(tmp_path: Path):
    base = tmp_path / 'base77f'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 1},
        references={1: [['1|', '0001', 'Иванов Иван Иванович']]}))
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--anonymize-fields', '_descr'])
    assert rc == 0
    objs = _load(out)
    assert objs[0]['attributes']['_descr'] == 'Иванов И. И.'


def test_extract_8x(tmp_path: Path):
    t = FixtureTable('_REFERENCE3', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=150),
    ])
    cd = tmp_path / 'base8x'
    cd.mkdir()
    write_fake_1cd(cd / '1Cv8.1CD', [t])
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(cd), '--out', str(out)])
    assert rc == 0
    objs = _load(out)
    assert len(objs) >= 0  # пустая таблица допустима; главное — JSON читается

# ---- Фаза 29.2: селективный перенос по разделам ----

def test_extract_8x_objects_physical_table(tmp_path: Path):
    """--objects Таблица._REFERENCE3 — только указанная физическая таблица."""
    fields = [FixtureField('_IDRREF', 'B', length=16),
              FixtureField('_CODE', 'NC', length=9)]
    t1 = FixtureTable('_REFERENCE3', fields=fields,
                      rows=[encode_row(fields, {'_CODE': '0001'})])
    t2 = FixtureTable('_REFERENCE10', fields=fields,
                      rows=[encode_row(fields, {'_CODE': '0002'})])
    cd = tmp_path / 'base8x2'
    cd.mkdir()
    write_fake_1cd(cd / '1Cv8.1CD', [t1, t2])
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(cd), '--out', str(out),
               '--objects', 'Таблица._REFERENCE3'])
    assert rc == 0
    objs = _load(out)
    types = {o['type'] for o in objs}
    assert types == {'Таблица._REFERENCE3'}


def test_extract_8x_objects_invalid_spec(tmp_path: Path):
    cd = tmp_path / 'base8x3'
    cd.mkdir()
    write_fake_1cd(cd / '1Cv8.1CD', [])
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(cd), '--out', str(out),
               '--objects', 'Номенклатура'])
    assert rc == 1  # CLIError: неверный формат


BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
REQUIRED_BASE_81 = pytest.mark.skipif(
    not BASE_81.is_file(),
    reason='реальная база 8.1 отсутствует (read-only)')


@REQUIRED_BASE_81
def test_extract_8x_objects_group_on_real_base():
    """Маппинг конфигурационных объектов на реальной базе: группа
    Справочник.* отбирает таблицы _REFERENCE*, не отбирает документы и
    служебные таблицы (без чтения данных)."""
    from onec_converter.objects_filter import parse_objects, selects
    from onec_converter.source_8x_file import read_metadata
    md = read_metadata(BASE_81)
    objects = md['objects']
    assert any(o['kind'] == 'Справочник' and o['table'] for o in objects)
    specs = parse_objects(['Справочник.*'])
    refs = [o['table'] for o in objects
            if o['kind'] == 'Справочник' and o['table']]
    for t in refs:
        assert selects(specs, 'Справочник', 'X', table=t), t
    # служебные таблицы (вне конфигурации) группой не выбираются
    assert not selects(specs, 'Таблица', '_REFS', table='_REFS')
    assert not selects(specs, 'Таблица', '_USERPASSWORD', table='_USERPASSWORD')


def test_extract_8x_named_types_real_base():
    """named=True: конфигурационные таблицы получают тип `kind.имя`
    (совместимо с правилами TOON migrate --rules), а не `Таблица.*`."""
    from onec_converter.cli import _extract_8x
    base_dir = Path(BASE_81).parent  # _extract_8x ждёт каталог с 1Cv8.1CD
    objs = _extract_8x(str(base_dir), 0, [], workers=1, named=True)
    named_types = {o['type'] for o in objs if o['type'].startswith('Справочник.')}
    table_types = {o['type'] for o in objs if o['type'].startswith('Таблица.')}
    assert named_types, 'named-режим должен давать типы Справочник.<имя>'
    assert table_types  # служебные/вне-конфигурационные остаются Таблица.*
    # хотя бы один справочник имеет реквизиты по именам (не физические _FldNNN)
    n = next(o for o in objs if o['type'].startswith('Справочник.'))
    attrs = n['attributes'] or {}
    assert not any(k.startswith('_') for k in attrs), attrs
    assert 'Код' in attrs or 'Наименование' in attrs or 'Ссылка' in attrs
