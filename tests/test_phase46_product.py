"""Фаза 46: продукт и документация — tamper-evident в README, feature matrix,
диалог LLM, constant-time в extension_83/README, health.errors диагностика,
notify.telegram_url экранирование, clone_db прогресс, recipe полного цикла."""
from __future__ import annotations

from pathlib import Path

from onec_converter.fake_1cd import encode_row
from onec_converter.notify import telegram_url


# ---- notify: экранирование telegram_url ----
def test_telegram_url_quotes_special_chars():
    url = telegram_url('tok:en/123', '-100 123@chat')
    assert 'tok%3Aen%2F123' in url
    assert '-100%20123%40chat' in url
    # экранирование не ломает базовый контракт
    assert url.startswith('https://api.telegram.org/bot')


# ---- health: реальная диагностика errors ----
def _build_db(path: Path, n: int = 3) -> None:
    from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd

    fields = [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=9),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE0', fields,
                     rows=[encode_row(fields, {'CODE': str(i)})
                           for i in range(n)]),
    ]))


def test_health_errors_lock_detection(tmp_path: Path):
    from onec_converter.health import base_health

    _build_db(tmp_path / '1Cv8.1CD')
    lock = tmp_path / '1Cv8.1CL'
    lock.write_bytes(b'\x00')
    rep = base_health(tmp_path)
    assert rep['ok'] is True
    assert rep['errors']  # блокировка другой сессией попала в диагностику
    assert any('1Cv8.1CL' in e for e in rep['errors'])


# ---- clone_db: прогресс-логирование ----
def test_clone_db_progress_logged(tmp_path: Path, capsys):
    from onec_converter.clone_db import clone_db

    src = tmp_path / 'src'
    src.mkdir()
    _build_db(src / '1Cv8.1CD')
    out = clone_db(src, tmp_path / 'tgt')
    assert out['ok'] is True
    log = capsys.readouterr().err
    assert '[progress' in log
    assert 'копирование' in log


def test_clone_db_progress_uses_WorkflowProgress():
    src = Path('src/onec_converter/clone_db.py').read_text(encoding='utf-8')
    assert 'WorkflowProgress' in src
    prog = Path('src/onec_converter/progress.py').read_text(encoding='utf-8')
    assert 'def log(' in prog and 'total: int = 0' in prog


# ---- README: tamper-evident + feature matrix ----
def test_readme_tamper_evident_section():
    r = Path('README.md').read_text(encoding='utf-8')
    assert 'Tamper-evident audit log' in r
    assert 'audit-verify' in r and '--cross-files' in r
    assert 'Feature matrix' in r


# ---- пример диалога LLM-агента ----
def test_llm_agent_dialog_example():
    p = Path('examples/llm_agent_dialog.md')
    assert p.is_file()
    t = p.read_text(encoding='utf-8')
    assert 'auto_map_schemas' in t and 'explain_diff' in t
    assert 'confidence' in t


# ---- extension_83/README: constant-time + rate-limit ----
def test_extension_readme_security_docs():
    t = Path('src/onec_converter/extension_83/README.md').read_text(
        encoding='utf-8')
    assert 'Совпадает' in t
    assert 'constant' in t.lower() or 'константн' in t
    assert 'СчётчикНеудач' in t or '5 неудач' in t


# ---- recipe полного цикла ----
def test_recipe_full_cycle_exists():
    p = Path('docs/recipes/полный-цикл-clone-load-verify-audit.md')
    assert p.is_file()
    t = p.read_text(encoding='utf-8')
    for step in ('clone-db', 'extract', 'transform', 'load', 'verify',
                 'audit', 'audit-verify'):
        assert step in t


# ---- CHANGELOG ----
def test_changelog_46():
    c = Path('CHANGELOG.md').read_text(encoding='utf-8')
    assert '0.29.0' in c
