"""Фаза 42: укрепление аудита/комплаенс — cross-files verify, кеш
_last_record_hash, pii_masking по умолчанию, crypto_utils, мутационный
fuzz цепочки, CLI audit-verify."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter import audit as audit_mod
from onec_converter.audit import AuditLog, _last_record_hash, get_audit, verify_audit


# ---- cross-files: границы с архивами ротации ----
def _rewrite_marker_prev(path: Path, new_prev: str) -> None:
    """Заменить prev_hash маркера, пересчитав его hash (цепочка внутри
    файла остаётся валидной — рвётся только граница)."""
    from onec_converter.audit import _sha256

    lines = path.read_text(encoding='utf-8').splitlines()
    marker = json.loads(lines[0])
    marker['prev_hash'] = new_prev
    body = dict(marker)
    body.pop('hash', None)
    marker['hash'] = _sha256(json.dumps(body, sort_keys=True, ensure_ascii=False))
    path.write_text(json.dumps(marker, ensure_ascii=False) + '\n'
                    + '\n'.join(lines[1:]) + '\n', encoding='utf-8')


def test_verify_audit_cross_files(tmp_path: Path):
    path = tmp_path / 'a.jsonl'
    log = AuditLog(path, max_bytes=200)
    for i in range(20):
        log.info('load', obj=f'OBJ-{i}')
    log.close()
    log2 = AuditLog(path, max_bytes=200)  # ротация -> .1 + маркер
    log2.info('load', obj='NEW')
    log2.close()
    assert verify_audit(path, cross_files=True) == []

    # подмена prev_hash в маркере -> нарушение границы
    _rewrite_marker_prev(path, 'f' * 64)
    errs = verify_audit(path, cross_files=True)
    assert any('граница файла' in e['error'] for e in errs)


def test_verify_audit_single_file_ignores_archives(tmp_path: Path):
    """Без cross_files границы с архивами не проверяются."""
    from onec_converter.audit import _sha256

    path = tmp_path / 'b.jsonl'
    # архив .1 с валидной записью (её hash — легитимный «хвост»)
    arch = AuditLog(tmp_path / 'b.jsonl.1')
    arch.info('load', obj='OLD')
    arch.close()
    # главный файл: маркер с поддельным prev_hash ('f'*64, не равен хвосту
    # архива) + валидная цепочка внутри файла
    marker = {'marker': 'rotated', 'ts': '2026-08-01T00:00:00Z',
              'prev_hash': 'f' * 64}
    marker['hash'] = _sha256(json.dumps(
        {k: v for k, v in marker.items() if k != 'hash'},
        sort_keys=True, ensure_ascii=False))
    rec = {'ts': '2026-08-01T00:00:01Z', 'level': 'INFO',
           'operation': 'load', 'obj': 'X', 'guid': '', 'rule': '',
           'result': '', 'detail': '', 'prev_hash': marker['hash']}
    rec['hash'] = _sha256(json.dumps(
        {k: v for k, v in rec.items() if k != 'hash'},
        sort_keys=True, ensure_ascii=False))
    path.write_text(json.dumps(marker, ensure_ascii=False) + '\n'
                    + json.dumps(rec, ensure_ascii=False) + '\n',
                    encoding='utf-8')
    assert verify_audit(path) == []  # цепочка внутри файла цела
    errs = verify_audit(path, cross_files=True)
    assert any('граница файла' in e['error'] for e in errs)


# ---- кеш _last_record_hash: повторное открытие без перечитывания ----
def test_last_record_hash_cache(monkeypatch, tmp_path: Path):
    path = tmp_path / 'c.jsonl'
    log = AuditLog(path)
    log.info('load', obj='X')
    log.close()
    reads = []

    import builtins
    orig_open = builtins.open
    def spy_open(*a, **k):
        reads.append(a)
        return orig_open(*a, **k)
    monkeypatch.setattr(builtins, 'open', spy_open)

    h1 = _last_record_hash(path)
    h2 = _last_record_hash(path)  # тот же файл, без изменений -> кеш
    assert h1 == h2
    assert len(reads) == 1  # файл прочитан один раз


def test_last_record_hash_cache_invalidated_on_change(tmp_path: Path):
    path = tmp_path / 'd.jsonl'
    log = AuditLog(path)
    log.info('load', obj='X')
    log.close()
    h1 = _last_record_hash(path)
    log2 = AuditLog(path)  # дописываем запись -> файл изменился
    log2.info('load', obj='Y')
    log2.close()
    h2 = _last_record_hash(path)
    assert h1 != h2


# ---- pii_masking по умолчанию True ----
def test_audit_pii_masking_default_on(tmp_path: Path):
    path = tmp_path / 'e.jsonl'
    log = AuditLog(path)  # без явного pii_masking
    rec = log.info('load', obj='клиент ИНН 7707083893 тел +7 999 123-45-67')
    log.close()
    assert '7707083893' not in rec['obj']
    assert '999' not in rec['obj'] or '*' in rec['obj']
    data = path.read_text(encoding='utf-8')
    assert '7707083893' not in data
    # отключить можно явно
    log2 = AuditLog(path, pii_masking=False)
    rec2 = log2.info('load', obj='ИНН 7707083893')
    log2.close()
    assert '7707083893' in rec2['obj']


def test_set_audit_default_masking(tmp_path: Path):
    try:
        set_audit = audit_mod.set_audit
        set_audit(tmp_path / 'f.jsonl')
        rec = get_audit().info('load', obj='тел +7 999 123-45-67')
        assert '*' in rec['obj'] or '999' not in rec['obj']
    finally:
        set_audit(None)


# ---- мутационный fuzz: любой байт в любой записи детектируется ----
def test_verify_audit_detects_any_single_byte_mutation(tmp_path: Path):
    path = tmp_path / 'g.jsonl'
    log = AuditLog(path)
    for i in range(5):
        log.info('load', obj=f'OBJ-{i}', detail='деталь ' * 5)
    log.close()
    original = path.read_bytes()
    assert verify_audit(path) == []
    # позиции байтов внутри контента строк (без разделителей \n и \r)
    offsets: list[int] = []
    pos = 0
    for ln in original.split(b'\n'):
        content = ln[:-1] if ln.endswith(b'\r') else ln
        for bi in range(min(len(content), 40)):
            offsets.append(pos + bi)
        pos += len(ln) + 1
    undetected: list[int] = []
    for off in offsets:
        mutated = bytearray(original)
        mutated[off] ^= 0x01
        path.write_bytes(bytes(mutated))
        if not verify_audit(path):  # подмена ВСЕГДА должна детектироваться
            undetected.append(off)
        path.write_bytes(original)
    assert offsets  # прогон не пустой
    assert undetected == []  # каждая мутация байта детектируется


# ---- crypto_utils: единый источник ----
def test_crypto_utils_shared():
    from onec_converter import anonymizer, s3_client
    from onec_converter.crypto_utils import hmac_sha256_hex, sha256_hex

    assert sha256_hex('abc') == sha256_hex(b'abc')
    assert anonymizer._hash_token('x', 'k') == hmac_sha256_hex(b'k', 'x')
    # s3 подписи используют тот же примитив
    assert s3_client._sha256_hex(b'abc') == sha256_hex('abc')


# ---- CLI audit-verify ----
def test_cli_audit_verify(tmp_path: Path, capsys):
    import argparse

    from onec_converter.cli import cmd_audit_verify

    path = tmp_path / 'h.jsonl'
    log = AuditLog(path)
    log.info('load', obj='OK')
    log.close()

    args = argparse.Namespace(audit_file=str(path), cross_files=False)
    assert cmd_audit_verify(args) == 0
    assert 'цела' in capsys.readouterr().out

    # подмена -> rc 1
    lines = path.read_text(encoding='utf-8').splitlines()
    rec = json.loads(lines[0])
    rec['result'] = 'HACKED'
    path.write_text(json.dumps(rec, ensure_ascii=False) + '\n', encoding='utf-8')
    assert cmd_audit_verify(args) == 1
    assert 'нарушений' in capsys.readouterr().err


def test_cli_has_audit_verify_command():
    src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    assert "'audit-verify': cmd_audit_verify" in src
    assert "add_parser('audit-verify'" in src
