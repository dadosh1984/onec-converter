"""Фаза 55: интерактивность и UX (0.38.0).

F1/F2  pretty ASCII-таблицы в TTY для inspect/query/stats
       (JSON остаётся при --no-pretty / не-TTY) + корневой --pretty/--no-pretty.
G1/G3  --help с категориями команд (Разведка/Перенос/Проверка/...).
H-fix  --help не падает на cp1251-консолях (reconfigure utf-8 в main).
terminal: is_tty + render_table (без внешних зависимостей).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from onec_converter import terminal


def _fake_base(tmp_path: Path) -> Path:
    """Небольшая фейковая 1CD с одной таблицей на 3 строки."""
    from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row, write_fake_1cd

    base = tmp_path / 'src'
    base.mkdir()
    t = FixtureTable('_REFERENCE1', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=8),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
    ])
    t.rows = [encode_row(t.fields, {'_CODE': f'{i:04d}', '_DESCRIPTION': f'Имя{i}'})
              for i in range(3)]
    write_fake_1cd(base / '1Cv8.1CD', [t])
    return base


def test_render_table_shapes_and_truncates():
    txt = terminal.render_table(['A', 'B'], [['x' * 60, 1], ['short', 2]])
    assert txt.startswith('┌') and txt.endswith('┘')
    assert 'x' * 40 not in txt  # колонка > max_col обрезается
    assert '…' in txt


def test_is_tty_detects_non_tty():
    assert terminal.is_tty() is False  # в pytest stdout — не TTY


def test_resolve_pretty_auto_and_flag():
    from onec_converter.cli import _resolve_pretty

    class _A:
        pretty = None
    assert _resolve_pretty(_A()) is False  # не TTY -> машиночитаемо

    class _B:
        pretty = True
    assert _resolve_pretty(_B()) is True
    assert _resolve_pretty(_B())  # принудительный pretty даже в не-TTY


def test_parser_has_pretty_flags():
    from onec_converter.cli import build_parser

    p = build_parser()
    flags = {a.option_strings[0] for a in p._actions if a.option_strings}
    assert '--pretty' in flags and '--no-pretty' in flags


def test_help_groups_categories():
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'PYTHONPATH': 'src', 'PYTHONIOENCODING': 'utf-8'}
    proc = subprocess.run([sys.executable, '-m', 'onec_converter.cli', '--help'],
                          capture_output=True, encoding='utf-8', errors='replace',
                          env=env, cwd=str(root), check=False)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    for cat in ('Разведка:', 'Перенос:', 'Проверка:', 'Отчёты и аудит:',
                'Служебные:'):
        assert cat in out
    for cmd in ('inspect', 'extract', 'map', 'transform', 'load'):
        assert cmd in out


class _A:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_stats_pretty_table(tmp_path, capsys):
    from onec_converter.cli import cmd_stats

    base = _fake_base(tmp_path)
    rc = cmd_stats(_A(source_dir=str(base), pretty=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert 'Таблиц' in out and 'Строк' in out and '┌' in out


def test_stats_default_json(tmp_path, capsys, monkeypatch):
    """pretty=None и не TTY -> по-прежнему JSON (pipe-совместимость)."""
    import json

    from onec_converter.cli import cmd_stats

    monkeypatch.setattr(sys.stdout, 'isatty', lambda: False)
    base = _fake_base(tmp_path)
    rc = cmd_stats(_A(source_dir=str(base), pretty=None))
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data['ok'] is True and 'rows' in data


def test_query_pretty_table(tmp_path, capsys):
    from onec_converter.cli import cmd_query

    base = _fake_base(tmp_path)
    rc = cmd_query(_A(source_dir=str(base), table='_REFERENCE1',
                      select='*', where='', order_by='', limit=2,
                      pretty=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert '┌' in out and '_CODE' in out


def test_help_does_not_crash_cp1251(capsys):
    """--help на cp1251-консоли не должен падать UnicodeEncodeError
    (H-fix: main reconfigure stdout/stderr в utf-8)."""
    from onec_converter.cli import main

    class _FakeStream:
        def __init__(self):
            self.data = []
        def write(self, s):
            self.data.append(s)
        def flush(self):
            pass
        def reconfigure(self, **kw):
            self.encoding = kw.get('encoding')
        def isatty(self):
            return False

    fs = _FakeStream()
    try:
        orig_out, orig_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = fs, fs
        import pytest as _pytest
        with _pytest.raises(SystemExit) as exc_info:
            main(['--help'])
        # --help exits 0 после печати; важно: не упал UnicodeEncodeError
        assert exc_info.value.code == 0
        joined = ''.join(d or '' for d in fs.data)
        assert 'Разведка' in joined
    finally:
        sys.stdout, sys.stderr = orig_out, orig_err
