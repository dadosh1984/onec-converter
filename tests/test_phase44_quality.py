"""Фаза 44: покрытие и качество — UZ-профиль PII, конфиг покрытия в
pyproject, mypy на scripts, тайминг gates.sh, check_bsl на несколько файлов."""
from __future__ import annotations

from pathlib import Path


# ---- PII_PROFILES: профиль Узбекистан (ИНН/ПИНФЛ) ----
def test_pii_profile_uzbekistan_exists():
    from onec_converter.anonymizer import PII_PROFILES

    assert 'uzbekistan' in PII_PROFILES
    prof = PII_PROFILES['uzbekistan']
    assert 'ПИНФЛ' in prof and 'ИНН' in prof and 'ФИО' in prof


def test_anonymizer_uzbekistan_profile_masks():
    from onec_converter.anonymizer import Anonymizer

    anon = Anonymizer(fields=['ПИНФЛ', 'ИНН'])
    out = anon.apply({'ПИНФЛ': '12345678901234', 'ИНН': '123456789',
                      'БИК': '00418'})
    assert out['ПИНФЛ'] != '12345678901234'
    assert out['ИНН'] != '123456789'
    assert out['БИК'] == '00418'  # вне профиля не трогается


def test_pii_scanner_detects_pinfl_uz():
    from onec_converter.pii_scanner import scan_text

    hits = [m.kind for m in scan_text('ПИНФЛ 51234567890123, тел +998 90 123 45 67',
                                      profile='UZ')]
    assert 'pinfl' in hits and 'phone' in hits


# ---- COVERAGE_MODULES: конфиг в pyproject.toml, расширен на Фазы 32-40 ----
def test_coverage_modules_in_pyproject():
    py = Path('pyproject.toml').read_text(encoding='utf-8')
    assert '[tool.onec-gates]' in py
    assert 'coverage_modules' in py
    for m in ('audit', 'clone_db', 'health', 's3_client', 'sql_source',
              'ai_skills'):
        assert f'"{m}"' in py or f"'{m}'" in py


def test_gates_reads_coverage_from_pyproject():
    src = Path('scripts/gates.sh').read_text(encoding='utf-8')
    assert 'onec-gates' in src or 'coverage_modules' in src
    assert 'COV_THRESHOLD' in src


# ---- mypy распространяется на scripts/ ----
def test_mypy_covers_scripts_in_gates():
    src = Path('scripts/gates.sh').read_text(encoding='utf-8')
    assert 'python -m mypy src scripts' in src


# ---- тайминг pytest в gates.sh + лимит ----
def test_gates_pytest_timing():
    src = Path('scripts/gates.sh').read_text(encoding='utf-8')
    assert 'PYTEST_TIME_LIMIT' in src
    assert 'elapsed' in src


# ---- check_bsl: несколько .bsl файлов ----
def test_check_bsl_multiple_files(tmp_path: Path, capsys):
    import sys
    sys.path.insert(0, 'scripts')
    from check_bsl import main  # type: ignore[import-not-found]

    good = tmp_path / 'a.bsl'
    good.write_text('Функция Один(Запрос) Экспорт\n', encoding='utf-8')
    dup = tmp_path / 'b.bsl'
    dup.write_text('Функция Один(Запрос) Экспорт\nФункция Один(Запрос) Экспорт\n',
                   encoding='utf-8')

    assert main([str(good)]) == 0
    assert '1 файл' in capsys.readouterr().out

    rc = main([str(good), str(dup)])
    assert rc == 1
    captured = capsys.readouterr()
    assert 'b.bsl' in captured.out  # дубликат найден во втором файле
    assert '1 проблема' in captured.out
