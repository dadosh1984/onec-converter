"""Фаза 45: AI-навыки глубже + CLI — confidence, save, ai-map/ai-explain,
mint-token --dry-run/--json, rate-limit в BSL."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.ai_skills import auto_map_schemas, compress_metadata, explain_diff

MS = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'synonym': '',
     'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'type': 'NC'}]},
    {'kind': 'Документ', 'name': 'Продажа', 'synonym': 'Реализация',
     'table': '_DOCUMENT56',
     'attributes': [{'name': 'Номер', 'type': 'NC'}]},
]}
MT = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'synonym': '',
     'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'type': 'NC'}]},
    {'kind': 'Документ', 'name': 'ПродажаТоваров', 'synonym': 'Реализация',
     'table': '_DOCUMENT99',
     'attributes': [{'name': 'Номер', 'type': 'NC'}]},
]}


# ---- confidence в auto_map_schemas ----
def test_auto_map_confidence_exact_vs_synonym():
    res = auto_map_schemas(MS, MT)
    by_src = {r['source']: r for r in res['rules']}
    assert by_src['Справочник.Банки']['confidence'] == 'exact'
    assert by_src['Документ.Продажа']['confidence'] == 'synonym'


# ---- compress_metadata: сохранение в файл ----
def test_compress_metadata_save(tmp_path: Path):
    out = tmp_path / 'summary.json'
    c = compress_metadata(MS, top_tables=5, out_path=out)
    assert out.is_file()
    saved = json.loads(out.read_text(encoding='utf-8'))
    assert saved['objects'] == c['objects'] == 2
    assert 'kinds' in saved and 'top' in saved


# ---- CLI: регистрация ai-map/ai-explain ----
def test_cli_ai_commands_registered():
    src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    assert "'ai-map': cmd_ai_map" in src
    assert "'ai-explain': cmd_ai_explain" in src
    assert "add_parser('ai-map'" in src and "add_parser('ai-explain'" in src


def test_cli_mint_token_dry_run_json():
    import argparse

    from onec_converter.cli import cmd_mint_token

    a = argparse.Namespace(secret='s', issuer='onec-converter', exp_min=5,
                           dry_run=True, json=False)
    assert cmd_mint_token(a) == 0

    b = argparse.Namespace(secret='s', issuer='onec-converter', exp_min=5,
                           dry_run=False, json=True)
    assert cmd_mint_token(b) == 0


def test_mint_token_dry_run_no_signature(capsys):
    import argparse

    from onec_converter.cli import cmd_mint_token

    a = argparse.Namespace(secret='s', issuer='onec-converter', exp_min=5,
                           dry_run=True, json=False)
    cmd_mint_token(a)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed['header']['alg'] == 'HS256'
    assert parsed['payload']['iss'] == 'onec-converter'
    assert 'signature' not in out  # dry-run: без подписи


# ---- rate-limit в Module.bsl ----
def test_bsl_rate_limit_present():
    bsl = Path('src/onec_converter/extension_83/Module.bsl').read_text(
        encoding='utf-8-sig')
    assert 'Перем СчётчикНеудач' in bsl
    assert 'СчётчикНеудач >= 5' in bsl
    assert 'СчётчикНеудач = СчётчикНеудач + 1' in bsl


def test_bsl_rate_limit_check_bsl_passes():
    import subprocess
    import sys

    rc = subprocess.run([sys.executable, 'scripts/check_bsl.py'],
                        capture_output=True, text=True, check=False)
    assert rc.returncode == 0, rc.stdout


# ---- explain_diff по-прежнему работает ----
def test_explain_diff_still_ok():
    reasons = explain_diff({'only_source': ['Справочник.К'], 'type_mismatch': [
        {'object': 'Документ.Продажа', 'attr': 'Сумма',
         'source_type': 'N', 'target_type': 'S'}]})
    assert any('Только в источнике' in r for r in reasons)
    assert any('Изменён тип' in r for r in reasons)
