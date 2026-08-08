"""Интеграционные тесты парсера 1Cv8.1CD на реальных базах (read-only).

Базы:
- `1C_8.1/1Cv8.1CD` — источник (1CD 8.3.8.0, 517 таблиц, конфигурация 8.1-эпохи,
  данные: 1141 запись «Банки РУз»);
- `1C_8.3/1Cv8.1CD` — приёмник («Бухгалтерия для Узбекистана 3.0», 8033 таблицы,
  без данных).
"""
from pathlib import Path

import pytest

from onec_converter.source_8x_file import (
    Database1CD,
    FormatError,
    read_dbschema,
    read_metadata,
    read_table,
)

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
BASE_83 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3/1Cv8.1CD')

REQUIRED = pytest.mark.skipif(
    not (BASE_81.is_file() and BASE_83.is_file()),
    reason='реальные базы недоступны')


def test_non_1cd_raises(tmp_path: Path):
    p = tmp_path / 'x.bin'
    p.write_bytes(b'not a 1cd file at all......')
    with pytest.raises(FormatError):
        Database1CD(p)


@pytest.mark.integration
@pytest.mark.parametrize('base', [BASE_81, BASE_83])
def test_real_base_header(base: Path):
    if not base.is_file():
        pytest.skip(f'база недоступна: {base}')
    db = Database1CD(base)
    try:
        assert str(db.version) == '8.3.8.0'
        assert db.total_pages > 0
        assert db.page_size in (4096, 8192)
    finally:
        db.close()


@REQUIRED
@pytest.mark.integration
def test_source_8_1_tables():
    with Database1CD(BASE_81) as db:
        tables = db.tables
        assert len(tables) == 517
        assert '_REFERENCE3' in tables
        assert '_ACC2' in tables
        assert 'DBSCHEMA' in tables and 'PARAMS' in tables and 'CONFIG' in tables
        assert db.locale == 'ru_RU'


@REQUIRED
@pytest.mark.integration
def test_source_8_1_dbnames_binding():
    md = read_metadata(BASE_81)
    objs = md['objects']
    assert len(objs) == 253
    kinds = {}
    for o in objs:
        kinds[o['kind']] = kinds.get(o['kind'], 0) + 1
    assert kinds == {'Справочник': 62, 'Документ': 136, 'Перечисление': 29,
                     'РегистрСведений': 23, 'РегистрНакопления': 2,
                     'ПланСчетов': 1}
    by_name = {o['name']: o for o in objs if o['kind'] == 'Справочник'}
    bank = by_name['Банки']
    assert bank['table'] == '_REFERENCE3'
    assert bank['ref_num'] == 3
    assert 'Код' in {a['name'] for a in bank['attributes']}
    assert 'Наименование' in {a['name'] for a in bank['attributes']}
    val = by_name['Валюты']
    assert val['table'] == '_REFERENCE5'
    # документы и перечисления присутствуют
    assert any(o['kind'] == 'Документ' for o in objs)
    assert any(o['kind'] == 'Перечисление' for o in objs)


@REQUIRED
@pytest.mark.integration
def test_source_8_1_rows():
    rows = list(read_table(BASE_81, '_REFERENCE3'))
    assert len(rows) == 1141
    # реальные банки Узбекистана
    with_code = [r for r in rows if r['_CODE'] and str(r['_CODE']).strip()]
    assert any('Банки РУз' in str(r['_DESCRIPTION']) for r in with_code)
    # GUID-ы ссылок — канонический вид
    ids = {r['_IDRREF'] for r in rows}
    assert len(ids) == 1141
    assert all(len(i) == 36 and i.count('-') == 4 for i in ids)


@REQUIRED
@pytest.mark.integration
def test_source_8_1_dbschema():
    schema = read_dbschema(BASE_81)
    # содержимое блоба — текстовое описание схемы (поля FldNNN, блоки ReferenceN)
    assert 'Reference3' in schema
    assert 'Fld' in schema
    assert len(schema) > 100_000


@REQUIRED
@pytest.mark.integration
def test_target_8_3_structure():
    """Приёмник 8.3: camelCase-стиль таблиц + огромный каталог."""
    md = read_metadata(BASE_83)
    assert len(md['tables']) > 8000
    # стиль 8.3: _Reference74
    assert any(t.startswith('_Reference') for t in md['tables'])


@REQUIRED
@pytest.mark.integration
def test_target_8_3_dbnames_style():
    """DBNames 8.3: 36k+ записей; связь объектов с таблицами через read_metadata."""
    with Database1CD(BASE_83) as db:
        dn = db.read_dbnames()
        assert len(dn) > 30_000
        # поля (Fld) — основная масса записей 8.3
        assert sum(1 for kind, _ in dn.values() if kind == 'Fld') > 20_000
    md = read_metadata(BASE_83)
    # объекты связаны с таблицами
    linked = [o for o in md['objects'] if o['table']]
    assert len(linked) > 1000
    # перечисления 8.3 -> _ENUMnn
    assert any(o['kind'] == 'Перечисление' and o['table'].startswith('_ENUM')
               for o in md['objects'])


@REQUIRED
@pytest.mark.integration
def test_source_8_1_ref_names():
    """A1: кеш ссылок GUID→наименование на реальной базе (родитель банка)."""
    with Database1CD(BASE_81) as db:
        t = db.tables['_REFERENCE3']
        f = t.fields
        parent_found = False
        for row in db.table_rows(t):
            if row[:1] == b'\x01':
                continue
            p = row[f['_PARENTIDRREF'].offset:
                    f['_PARENTIDRREF'].offset + 16]
            if p != b'\x00' * 16:
                name = db.ref_name('_REFERENCE3', p)
                assert name and 'Банк' in name, f'имя родителя: {name!r}'
                parent_found = True
                break
        assert parent_found, 'нет записей с родителем в Банках'
        # кеш построен и покрывает справочник
        assert len(db._ref_table_cache['_REFERENCE3']) >= 1000
