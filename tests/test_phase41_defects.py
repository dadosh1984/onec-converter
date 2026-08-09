"""Фаза 41: хирургические дефекты раунда 4 — openapi-версия/Bearer, маркер
ротации audit, валидация prev_hash первой записи, anti-injection sql_source."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter import __version__
from onec_converter.audit import AuditLog, verify_audit
from onec_converter.sql_source import GenericSqlSource, SqlSourceError


# ---- находка №1: версия в openapi.yaml == __version__ ----
def test_openapi_version_matches_package():
    yaml = Path('docs/openapi.yaml').read_text(encoding='utf-8')
    m = next(l for l in yaml.splitlines() if l.strip().startswith('version:'))
    assert m.split(':', 1)[1].strip() == __version__


# ---- находка №2: BearerAuth на /metadata и /load ----
def test_openapi_bearer_auth_on_both_paths():
    yaml = Path('docs/openapi.yaml').read_text(encoding='utf-8')
    assert '/metadata' in yaml and '/load' in yaml
    assert yaml.count('- BearerAuth: []') == 2


# ---- генератор не расходится с закоммиченной спекой ----
def test_gen_openapi_regenerates_identical():
    import sys
    sys.path.insert(0, 'scripts')
    import gen_openapi  # type: ignore[import-not-found]
    yaml = gen_openapi.build_openapi(gen_openapi.collect_endpoints(),
                                     gen_openapi.collect_handlers())
    assert yaml == Path('docs/openapi.yaml').read_text(encoding='utf-8')


# ---- находка №3-4: ротация пишет маркер; verify_audit проверяет корень ----
def test_audit_rotation_writes_marker_and_chains(tmp_path: Path):
    path = tmp_path / 'a.jsonl'
    log = AuditLog(path, max_bytes=200)
    for i in range(20):
        log.info('load', obj=f'OBJ-{i}')
    log.close()
    assert verify_audit(path) == []

    # переоткрытие при превышении лимита -> ротация в .1
    log2 = AuditLog(path, max_bytes=200)
    log2.info('load', obj='NEW')
    log2.close()

    bak = path.with_suffix(path.suffix + '.1')
    assert bak.is_file()  # архив старых записей
    lines = path.read_text(encoding='utf-8').splitlines()
    marker = json.loads(lines[0])
    assert marker.get('marker') == 'rotated'
    assert marker.get('prev_hash')  # ссылка на хеш из .1
    # цепочка в новом файле (маркер -> NEW) непротиворечива
    assert verify_audit(path) == []

    # третье открытие продолжает цепочку от маркера
    log3 = AuditLog(path, max_bytes=200)
    log3.info('load', obj='ANOTHER')
    log3.close()
    assert verify_audit(path) == []


def test_audit_verify_flags_forged_first_prev_hash(tmp_path: Path):
    """Подмена prev_hash в первой записи (без маркера ротации) — нарушение."""
    path = tmp_path / 'b.jsonl'
    rec = {'ts': '2026-08-01T00:00:00Z', 'level': 'INFO',
           'operation': 'load', 'obj': 'X', 'guid': '', 'rule': '',
           'result': '', 'detail': '', 'prev_hash': 'deadbeef'}
    path.write_text(json.dumps(rec, ensure_ascii=False) + '\n', encoding='utf-8')
    errs = verify_audit(path)
    assert any('первая запись' in e['error'] for e in errs)


def test_audit_verify_first_record_empty_prev_ok(tmp_path: Path):
    path = tmp_path / 'c.jsonl'
    log = AuditLog(path)
    log.info('load', obj='OK')
    log.close()
    assert verify_audit(path) == []


# ---- находка №5: sql_source anti-injection ----
class _SpyCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed: list[str] = []

    @property
    def description(self):
        return [('table_name',)]

    def execute(self, sql, params=None):
        self.executed.append(sql)
        return self

    def fetchall(self):
        return self._rows

    def fetchmany(self, size=1):
        rows = self._rows[:size]
        self._rows = self._rows[size:]
        return rows

    def close(self):
        pass


class _SpyConn:
    def __init__(self, rows=None):
        self._cur = _SpyCursor(rows)
        self.closed = False

    def cursor(self):
        return self._cur

    def close(self):
        self.closed = True


class _SpyDriver:
    def __init__(self, rows=None):
        # по умолчанию — каталог таблиц (для list_tables/fetch_metadata)
        self._rows = rows if rows is not None else [
            ('_Reference7', ''), ('_InfoRg10', '')]

    def connect(self, dsn):
        return _SpyConn(self._rows)


def test_sql_fetch_rows_quotes_and_rejects_injection():
    src = GenericSqlSource('postgres', 'dsn', _SpyDriver([(1,)]))
    rows = list(src.fetch_rows('_Reference7'))  # генератор — потребляем
    conn = src._connect()
    assert conn._cur.executed == ['SELECT * FROM "_Reference7"']
    assert rows == [{'table_name': 1}]

    with pytest.raises(SqlSourceError, match='недопустимое имя таблицы'):
        list(src.fetch_rows('_Reference7; DROP TABLE t'))

    with pytest.raises(SqlSourceError, match='недопустимое имя таблицы'):
        list(src.fetch_rows('x y'))
    src.close()


def test_sql_fetch_rows_mssql_quoting():
    src = GenericSqlSource('mssql', 'dsn', _SpyDriver([]))
    list(src.fetch_rows('_InfoRg10'))
    assert src._connect()._cur.executed == ['SELECT * FROM [_InfoRg10]']
    src.close()


def test_sql_metadata_mssql_where_parens():
    """AND связывается с LIKE, а не глотает OR — скобки в col_sql."""
    src = GenericSqlSource('mssql', 'dsn', _SpyDriver())
    src.fetch_metadata()
    col_sql = next(s for s in src._connect()._cur.executed
                   if 'COLUMNS' in s)
    assert 'AND (COLUMN_NAME' in col_sql
    src.close()
