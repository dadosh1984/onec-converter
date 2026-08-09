"""Progress-бар переноса (stderr, не ломает JSON stdout)."""
from __future__ import annotations

import io

from onec_converter.progress import TermProgress


def test_progress_counts_and_tables():
    out = io.StringIO()
    p = TermProgress(10, out=out)
    p.update('Справочник.Номенклатура', '_Reference98')
    p.update('Справочник.Номенклатура', '_Reference98')
    p.update('Документ.Доверенность', '_Document625')
    assert p.done == 3
    assert p.tables == {'_Reference98': 2, '_Document625': 1}
    p.finish({'total': 3})
    txt = out.getvalue()
    assert 'перенос завершён' in txt or 'итого' in txt


def test_progress_ntty_sparse_output():
    """В не-TTY прогресс печатается редко (не каждый объект)."""
    out = io.StringIO()
    p = TermProgress(100, out=out)  # non-tty StringIO
    for i in range(100):
        p.update('Справочник.X', '_ReferenceX')
        p.draw('Справочник.X', '_ReferenceX')
    assert p.done == 100
    lines = out.getvalue().splitlines()
    # компактно: не по строке на каждый объект, а только по узлам прогресса
    assert len(lines) < 100


def test_progress_zero_total_safe():
    out = io.StringIO()
    p = TermProgress(0, out=out)
    p.finish({'total': 0})
    # 0/1 не даёт деления на ноль; выводится "перенос завершён"
    assert 'завершён' in out.getvalue() or 'итого' in out.getvalue()
