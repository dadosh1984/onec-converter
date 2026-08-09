"""Фаза 37: безопасность и комплаенс — pii_scanner, tamper-audit, RBAC, отчёт."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from onec_converter.pii_scanner import field_is_pii, luhn_valid, scan_record, scan_text


def _audit_path(tmp_path: Path) -> Path:
    return tmp_path / 'audit.jsonl'


# ---- pii_scanner ----
def test_scan_inn_snils_phone_email():
    text = 'ИНН 7707083893, СНИЛС 123-456-789-01, +7 (495) 123-45-67, a@b.ru'
    kinds = {m.kind for m in scan_text(text)}
    assert 'inn' in kinds and 'snils' in kinds
    assert 'phone' in kinds and 'email' in kinds


def test_scan_uz_profile():
    text = 'тел +998 90 123 45 67; ПИНФЛ 50301000123456'
    ru = {m.kind for m in scan_text(text, profile='RU')}
    uz = {m.kind for m in scan_text(text, profile='UZ')}
    assert 'pinfl' in uz  # ПИНФЛ только в UZ-профиле
    assert 'pinfl' not in ru
    assert 'phone' in uz


def test_luhn_and_card_detection():
    # валидный номер (пример Луна) vs невалидный
    assert luhn_valid('4111111111111111') is True
    assert luhn_valid('4111111111111112') is False
    # найдётся только прошедший Луна
    kinds = {m.kind for m in scan_text('Карта 4111 1111 1111 1111')}
    assert 'card' in kinds


def test_scan_record_and_field():
    rec = {'ФИО': 'Иванов', 'ИНН': '7707083893', 'Комментарий': 'просто'}
    hits = scan_record(rec)
    assert [f for f, _ in hits] == ['ИНН']
    assert field_is_pii('СНИЛС') and field_is_pii('Телефон')
    assert not field_is_pii('Наименование')


# ---- audit tamper-evident + redact ----
def test_audit_hash_chain_and_verify(tmp_path: Path):
    from onec_converter.audit import AuditLog, verify_audit

    log = AuditLog(_audit_path(tmp_path))
    log.info('load', obj='A')
    log.warning('transform', obj='B')
    log.close()
    assert verify_audit(_audit_path(tmp_path)) == []
    # повреждение записи ловится
    p = _audit_path(tmp_path)
    text = p.read_text(encoding='utf-8')
    p.write_text(text.replace('"obj": "A"', '"obj": "X"'), encoding='utf-8')
    assert verify_audit(p) != []


def test_audit_pii_masking(tmp_path: Path):
    from onec_converter.audit import AuditLog, read_audit

    p = tmp_path / 'redact.jsonl'
    a = AuditLog(p, pii_masking=True)
    a.info('load', obj='ИНН 7707083893 клиент')
    a.close()
    recs = read_audit(p)
    assert '7707083893' not in recs[0]['obj']
    assert '***' in recs[0]['obj']


# ---- RBAC MCP ----
def test_mcp_rbac_blocks_inspect(monkeypatch):
    from onec_converter import mcp_server as m

    monkeypatch.setenv('ONEC_MCP_ROLE', 'inspect')
    assert m._current_role() == 'inspect'
    with pytest.raises(m.RbacError):
        m._require_role('load', 'load_direct')


def test_mcp_rbac_allows_load(monkeypatch):
    from onec_converter import mcp_server as m

    monkeypatch.setenv('ONEC_MCP_ROLE', 'load')
    m._require_role('load', 'load_direct')  # не бросает
    monkeypatch.delenv('ONEC_MCP_ROLE', raising=False)
    m._require_role('load', 'load_direct')  # по умолчанию load


# ---- pii-report CLI / gdpr ----
def test_pii_report_cli(tmp_path: Path, capsys):
    from onec_converter.audit import AuditLog
    p = _audit_path(tmp_path)
    log = AuditLog(p)
    log.info('load', obj='Справочник.Банки')
    log.close()

    import argparse

    from onec_converter.cli import cmd_pii_report

    rc = cmd_pii_report(argparse.Namespace(audit_file=str(p), rules_file='',
                                            profile='RU'))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True and out['generated'] == 1
    assert out['tamper_evident'] is True


def test_gdpr_report_rules_fields(tmp_path: Path):
    from onec_converter.audit import AuditLog
    p = _audit_path(tmp_path)
    log = AuditLog(p)
    log.info('transform', obj='X')
    log.close()
    rules = tmp_path / 'rules.json'
    rules.write_text(json.dumps({'version': 1, 'enums': {}, 'objects': [{
        'source': 'A', 'target': 'B',
        'attributes': {'ИНН': 'ИНН', 'Наименование': 'Наименование'}}]}),
        encoding='utf-8')
    from onec_converter.gdpr_152_report import gdpr_report
    rep = gdpr_report(p, rules)
    assert 'ИНН' in rep['pii_fields']
    assert 'Наименование' not in rep['pii_fields']
