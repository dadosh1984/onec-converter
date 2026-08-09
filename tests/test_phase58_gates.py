"""Фаза 58: производительность и ворота (0.41.0).

H1  gates.sh all включает benchmark (проверка через чтение скрипта).
H2  контракт: количество/имена тулов cmd_mcp == mcp_server @visible_tool.
H4  COVERAGE_MODULES — один источник в pyproject (gates.sh читает оттуда).
H5  hypothesis fuzz audit hash-цепочки: любая мутация записи ломает verify.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from onec_converter.audit import verify_audit

pytest.importorskip('hypothesis')
from datetime import timedelta

from hypothesis import given, settings
from hypothesis import strategies as st


# ---- H1: benchmark в gates.sh all ----
def test_gates_all_includes_benchmark():
    gates = Path('scripts/gates.sh').read_text(encoding='utf-8')
    assert 'run_benchmark' in gates
    m = re.search(r"all\)\s+(.*?);;", gates, flags=re.DOTALL)
    assert m and 'run_benchmark' in m.group(1)


# ---- H4: единый источник COVERAGE_MODULES (pyproject) ----
def test_coverage_modules_single_source():
    import tomllib

    with open('pyproject.toml', 'rb') as f:
        cfg = tomllib.load(f)
    expected = cfg['tool']['onec-gates']['coverage_modules']
    assert isinstance(expected, list) and expected
    gates = Path('scripts/gates.sh').read_text(encoding='utf-8')
    # ИМЕНА модулей НЕ должны быть захардкожены строкой в gates.sh
    # (объявление COVERAGE_MODULES=() пустое + заполняется из pyproject).
    # Выбираем реальное имя модуля из pyproject и проверяем, что оно не
    # встречается как литерал массива в скрипте.
    sample = expected[0]
    assert sample in gates  # это имя читается в цикле (упоминается)
    # сам массив не содержит литеральных имён: между COVERAGE_MODULES=( и )
    # в объявлении ничего нет (заполняется циклом из pyproject)
    assert re.search(r'COVERAGE_MODULES=\(\)', gates)


# ---- H2: контракт тулов cmd_mcp == mcp_server ----
def test_cli_mcp_tools_match_server():
    from onec_converter.cli import cmd_mcp
    from onec_converter.mcp_server import mcp

    slist = mcp._tool_manager.list_tools()
    server_names = {t.name for t in slist}

    class _A:
        stdio = False
        sse = False
    import io
    import sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = cmd_mcp(_A())
    finally:
        sys.stdout = old
    assert rc == 0
    data = json.loads(buf.getvalue())
    cli_names = {t['name'] for t in data['tools']}
    assert cli_names == server_names


# ---- H5: fuzz audit hash-цепочки ----
@given(st.lists(st.text(max_size=30), min_size=1, max_size=8))
@settings(deadline=timedelta(seconds=3))
def test_audit_chain_fuzz(objs):
    import tempfile

    from onec_converter.audit import AuditLog

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'audit.jsonl'
        log = AuditLog(p)
        for o in objs:
            log.info('load', obj=o or 'X', result='ok')
        log.close()
        assert verify_audit(p) == []  # цепочка цела


@given(st.text(max_size=20))
@settings(deadline=timedelta(seconds=3))
def test_audit_chain_mutation_breaks(mut):
    import tempfile

    from onec_converter.audit import AuditLog, _sha256

    if not mut:
        return
    # гарантируем РЕАЛЬНУЮ подмену: если mut совпал с исходным значением "A"
    # (или вызывает коллизию сериализации), стэйк цепочки не рвётся
    # (второй хэш = prev_hash по-прежнему сходится) — тест станет бессмысленным.
    mut = '~MUT~' if mut in ('A', 'B') else mut
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'audit.jsonl'
        log = AuditLog(p)
        log.info('load', obj='A', result='ok')
        log.info('load', obj='B', result='ok')
        log.close()
        # подменить obj в первой записи (сохранив hash словно он пересчитан)
        lines = p.read_text(encoding='utf-8').splitlines()
        r0 = json.loads(lines[0])
        r0['obj'] = mut
        body = dict(r0); body.pop('hash', None)
        r0['hash'] = _sha256(json.dumps(body, sort_keys=True, ensure_ascii=False))
        p.write_text(json.dumps(r0, ensure_ascii=False) + '\n'
                     + '\n'.join(lines[1:]) + '\n', encoding='utf-8')
        errs = verify_audit(p)
        assert errs, 'мутация ОБЯЗАНА разорвать цепочку (prev_hash следующий)'
