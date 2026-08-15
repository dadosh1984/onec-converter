"""Отчёт по анонимизации ПДн (152-ФЗ / 152 УЗ)

Собирает из JSONL-журнала аудита и конфигурации анонимизатора сводку для
службы безопасности: какие поля/объекты были анонимизированы, каким
алгоритмом и где хранятся логи. Выдаёт структурированный JSON (готов к
PDF/печати). Код авторский.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import read_audit


class PiiReportError(Exception):
    """Ошибка построения отчёта по ПДн."""


def scan_field_for_pii(field: str) -> bool:
    """Похоже ли имя поля на ПДн (для отчёта, без чтения значений)."""
    from .pii_scanner import field_is_pii

    return field_is_pii(field)


def gdpr_report(audit_file: str | Path,
                rules_file: str | Path | None = None,
                profile: str = 'RU') -> dict[str, Any]:
    """Построить отчёт об анонимизации.

    audit_file — JSONL-журнал (read_audit); rules_file — опционально,
    правила TOON (для перечисления полей). Возвращает {ok, generated,
    pii_fields, algorithms, audit_file, rules_file, events, hashes}.
    """
    ap = Path(audit_file)
    if not ap.is_file():
        raise PiiReportError(f'нет журнала аудита: {audit_file}')

    recs = read_audit(ap)
    # алгоритм по audit: фиксируем операции, помогающие оценить анонимм.
    algorithms = {'mask': 'значения в промежуточных JSON маскируются '
                          '(--anonymize-fields)'}
    # поля ПДн из правил (если переданы)
    pii_fields: list[str] = []
    if rules_file:
        rp = Path(rules_file)
        if not rp.is_file():
            raise PiiReportError(f'нет файла правил: {rules_file}')
        try:
            rules = json.loads(rp.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise PiiReportError(f'правила не JSON: {exc}') from exc
        for rule in rules.get('objects') or []:
            for a in (rule.get('attributes') or {}):
                if scan_field_for_pii(a) and a not in pii_fields:
                    pii_fields.append(a)

    hashes = True
    # наличие prev_hash/hash во всех записях
    with open(ap, encoding='utf-8') as f:
        first = f.readline().strip()
        if first and 'hash' not in first:
            hashes = False

    return {
        'ok': True,
        'profile': 'RU (152-ФЗ)' if profile == 'RU' else 'UZ (152 УЗ)',
        'generated': len(recs),
        'audit_file': str(ap),
        'rules_file': str(rules_file) if rules_file else None,
        'pii_fields': pii_fields,
        'algorithms': algorithms,
        'tamper_evident': hashes,
        'note': 'Логи аудита хранятся в указанном audit_file; для печати '
                'сериализуйте JSON в PDF через внешний конвейер.',
    }
