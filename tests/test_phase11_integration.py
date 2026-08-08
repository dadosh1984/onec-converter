"""Интеграционные тесты Фазы 11 на реальных базах (read-only).

query / guid-diff / config-versions против 1C_8.1 и 1C_8.3. Базы не
изменяются (только чтение); при отсутствии — тест пропускается.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.config_versions import config_versions
from onec_converter.guid_diff import guid_diff
from onec_converter.query import query_table_sql
from onec_converter.source_8x_file import Database1CD

BASE_81 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD')
BASE_83 = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3/1Cv8.1CD')
NEED_83 = pytest.mark.skipif(
    not BASE_83.is_file(), reason='реальная база 8.3 отсутствует')
NEED_BOTH = pytest.mark.skipif(
    not (BASE_81.is_file() and BASE_83.is_file()),
    reason='реальные базы 8.1/8.3 отсутствуют')


@NEED_83
@pytest.mark.integration
def test_query_sql_on_real_83():
    with Database1CD(BASE_83) as db:
        rows = query_table_sql(db, 'PARAMS', select='FILENAME,DATASIZE',
                               where="FILENAME LIKE '%inf%'",
                               order_by='DATASIZE DESC', limit=5)
        assert rows
        assert all(r['FILENAME'] for r in rows)
        # сортировка по размеру — невозрастающая
        sizes = [r['DATASIZE'] for r in rows]
        assert sizes == sorted(sizes, reverse=True)


@NEED_83
@pytest.mark.integration
def test_query_sql_ref_columns_real_83():
    """REF-поля (B 16 байт) декодируются в GUID; проекция работает."""
    with Database1CD(BASE_83) as db:
        tab = next((n for n, t in db.tables.items()
                    if '_IDRREF' in t.fields), None)
        if tab is None:
            pytest.skip('нет таблицы с _IDRREF')
        rows = query_table_sql(db, tab, select='_IDRREF', limit=3)
        for r in rows:
            guid = r['_IDRREF']
            assert isinstance(guid, str) and '-' in guid


@NEED_BOTH
@pytest.mark.integration
def test_guid_diff_real_bases():
    rep = guid_diff(BASE_81, BASE_83)
    assert rep['ok'] is True
    assert rep['objects']['total_source'] > 0
    assert rep['objects']['total_target'] > 0
    assert 'only_source' in rep['objects']
    assert 'only_target' in rep['objects']
    # разные конфигурации — GUID не обязаны совпадать, отчёт структурен


@NEED_83
@pytest.mark.integration
def test_guid_diff_self_full():
    """База идентична себе: каждый GUID присутствует, full=True."""
    rep = guid_diff(BASE_83, BASE_83)
    assert rep['full'] is True
    assert rep['objects']['common'] == rep['objects']['total_source']
    assert rep['tables']['common'] == rep['tables']['total_source']


@NEED_83
@pytest.mark.integration
def test_config_versions_real_83():
    rep = config_versions(BASE_83)
    assert rep['ok'] is True
    assert rep['format'].startswith('8.3')
    assert rep['ibversion']
    assert rep['config_files']['CONFIG']['count'] > 0
