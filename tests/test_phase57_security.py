"""Фаза 57: безопасность (0.40.0).

E3  секреты из env ONEC_SECRET / stdin (mint-token, load) — не в ps/history.
E4  snapshot-политика записи: snapshot=True сохраняет откат-копию,
    snapshot=False (--no-snapshot) не создаёт её.
_ resolve_secret приоритет: флаг > env > TTY-ввод.
"""
from __future__ import annotations

import json
from pathlib import Path


def test_mint_token_uses_env_secret(tmp_path, monkeypatch, capsys):
    from onec_converter.cli import cmd_mint_token

    class _A:
        dry_run = False
        json = True
        issuer = 'test'
        exp_min = 5
        kid = ''
        secret = ''  # не задан флагом

    monkeypatch.setenv('ONEC_SECRET', 'env-secret-123')
    rc = cmd_mint_token(_A())
    assert rc == 0
    token = json.loads(capsys.readouterr().out)['token']
    assert len(token) > 20  # JWT содержит подпись HS256


def test_mint_token_no_secret_errors(monkeypatch, capsys):
    from onec_converter.cli import cmd_mint_token

    monkeypatch.delenv('ONEC_SECRET', raising=False)

    class _A:
        dry_run = False
        json = False
        issuer = 'x'
        exp_min = 1
        kid = ''
        secret = ''

    rc = cmd_mint_token(_A())
    assert rc == 1
    assert 'секрет' in capsys.readouterr().err


def test_resolve_secret_priority_flag_over_env(monkeypatch):
    from onec_converter.cli import _resolve_secret

    monkeypatch.setenv('ONEC_SECRET', 'from-env')
    assert _resolve_secret('from-flag') == 'from-flag'
    assert _resolve_secret('') == 'from-env'


def test_load_direct_snapshot_policy(tmp_path, monkeypatch):
    """E4 (Фаза 57): snapshot-копия приёмника управляется флагом snapshot.
    snapshot=True сохраняет копию для отката; snapshot=False — не создаёт
    (политика «--no-snapshot» вместо авто-удаления, чтобы не ломать
    гарантию отката/инспекции)."""
    from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
    from onec_converter.load_8x import load_direct
    from onec_converter.write_8x import create_1cd

    F_REF = [
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
    ]
    META = {'objects': [
        {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
         'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                         'length': 9, 'precision': 0}]},
    ]}
    tgt = tmp_path / 'target'
    tgt.mkdir()
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=F_REF,
                             rows=[encode_row(F_REF, {'_IDRREF': b'\x11' * 16,
                                                      '_CODE': 'seed'})])])
    monkeypatch.setattr('onec_converter.load_8x.read_metadata', lambda p: META)
    objs = [{'type': 'Справочник.Банки', 'key': ['0042'],
             'attributes': {'Код': '0042'}, 'references': {}}]
    # snapshot=True: копия создаётся и сохраняется (гарантия отката)
    rep = load_direct(str(tgt), objs, workdir=str(tmp_path / 'wd1'),
                      verify_after=False, snapshot=True)
    assert rep['snapshot'] and Path(rep['snapshot']).is_file()
    # snapshot=False: копия не создаётся (политика очистки на успехе)
    rep2 = load_direct(str(tgt), objs, workdir=str(tmp_path / 'wd2'),
                       verify_after=False, snapshot=False)
    assert rep2['snapshot'] is None
    assert (tmp_path / 'wd2' / '1Cv8.1CD').is_file()
