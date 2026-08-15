"""
Движок проверок после миграции: правила НСБУ для верификации перенесённых данных.

ponytail: rung 2 — паттерн из 1c-audit (Laravel AuditRuleInterface), портирован на Python.
"""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Результат одной проверки."""
    rule: str
    passed: bool
    object_name: str = ''
    field: str = ''
    expected: str = ''
    actual: str = ''
    severity: str = 'error'  # error | warning | info


@dataclass
class ValidationReport:
    """Сводный отчёт по всем проверкам."""
    results: list[ValidationResult] = field(default_factory=list)
    total_errors: int = 0
    total_warnings: int = 0

    @property
    def ok(self) -> bool:
        return self.total_errors == 0


class AuditRule(ABC):
    """Интерфейс правила проверки (аналог AuditRuleInterface из 1c-audit)."""

    @abstractmethod
    def check(self, sqlite_path: str | Path) -> list[ValidationResult]: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class NegativeBalanceRule(AuditRule):
    """Поиск красного сальдо: отрицательные остатки по счетам НСБУ."""

    name = 'negative_balance'

    def check(self, sqlite_path: str | Path) -> list[ValidationResult]:
        con = sqlite3.connect(str(sqlite_path))
        con.row_factory = sqlite3.Row
        results: list[ValidationResult] = []
        try:
            # Ищем таблицы регистра бухгалтерии
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                if 'Хозрасчетный' not in t and 'Accounting' not in t and 'AccRg' not in str(t):
                    continue
                # Проверяем отрицательные суммы
                cols = [d[1] for d in con.execute(
                    f'PRAGMA table_info([{t}])').fetchall()]
                amount_cols = [c for c in cols
                              if 'Сумма' in c or 'Amount' in c or 'сумма' in c.lower()]
                for ac in amount_cols:
                    try:
                        neg = con.execute(
                            f'SELECT COUNT(*) FROM [{t}] '
                            f'WHERE CAST([{ac}] AS REAL) < 0'
                        ).fetchone()[0]
                        if neg:
                            results.append(ValidationResult(
                                rule=self.name, passed=False,
                                object_name=t, field=ac,
                                actual=f'{neg} отрицательных значений',
                                severity='warning',
                            ))
                    except Exception:
                        pass
        finally:
            con.close()
        if not results:
            results.append(ValidationResult(rule=self.name, passed=True))
        return results


class EmptySubcontoRule(AuditRule):
    """Проверка заполнения субконто: NULL в ключевых полях."""

    name = 'empty_subconto'

    # Счета НСБУ, где субконто обязательны (упрощённый список)
    REQUIRED_FIELDS = [
        'Номенклатура', 'Контрагент', 'Договор', 'Склад',
        'СтатьяДвиженияДенежныхСредств', 'Подразделение',
    ]

    def check(self, sqlite_path: str | Path) -> list[ValidationResult]:
        con = sqlite3.connect(str(sqlite_path))
        con.row_factory = sqlite3.Row
        results: list[ValidationResult] = []
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                if not t.startswith('Справочник.'):
                    continue
                cols = [d[1] for d in con.execute(
                    f'PRAGMA table_info([{t}])').fetchall()]
                for rf in self.REQUIRED_FIELDS:
                    if rf in cols:
                        try:
                            empty = con.execute(
                                f'SELECT COUNT(*) FROM [{t}] '
                                f'WHERE [{rf}] IS NULL OR [{rf}] = ""'
                            ).fetchone()[0]
                            if empty:
                                results.append(ValidationResult(
                                    rule=self.name, passed=False,
                                    object_name=t, field=rf,
                                    actual=f'{empty} пустых значений',
                                    severity='warning',
                                ))
                        except Exception:
                            pass
        finally:
            con.close()
        if not results:
            results.append(ValidationResult(rule=self.name, passed=True))
        return results


class RowCountMismatchRule(AuditRule):
    """Сравнение количества строк source vs target после переноса."""

    name = 'row_count_mismatch'

    def __init__(self, source_sqlite: str | Path):
        self._source_sqlite = str(source_sqlite)

    def check(self, sqlite_path: str | Path) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        src_con = sqlite3.connect(self._source_sqlite)
        tgt_con = sqlite3.connect(str(sqlite_path))
        try:
            src_tables = {r[0] for r in src_con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if not r[0].startswith('_') and r[0] != 'sqlite_sequence'}
            tgt_tables = {r[0] for r in tgt_con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if not r[0].startswith('_') and r[0] != 'sqlite_sequence'}
            common = src_tables & tgt_tables
            for t in sorted(common):
                try:
                    src_cnt = src_con.execute(
                        f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
                    tgt_cnt = tgt_con.execute(
                        f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
                    if src_cnt != tgt_cnt:
                        results.append(ValidationResult(
                            rule=self.name, passed=False,
                            object_name=t,
                            expected=str(src_cnt),
                            actual=str(tgt_cnt),
                            severity='error' if tgt_cnt == 0 else 'warning',
                        ))
                except Exception:
                    pass
        finally:
            src_con.close()
            tgt_con.close()
        if not results:
            results.append(ValidationResult(rule=self.name, passed=True))
        return results


# Реестр правил
_BUILTIN_RULES: list[type[AuditRule]] = [
    NegativeBalanceRule,
    EmptySubcontoRule,
]


def validate_migration(
    target_sqlite: str | Path,
    source_sqlite: str | Path | None = None,
    rules: list[AuditRule] | None = None,
) -> ValidationReport:
    """Прогнать все правила проверки на результате миграции.

    Args:
        target_sqlite: путь к SQLite после apply_mapping (результат переноса)
        source_sqlite: путь к исходному SQLite (для сравнения строк)
        rules: список правил (None = встроенные)

    Returns:
        ValidationReport с результатами всех проверок
    """
    if rules is None:
        rules = [r() for r in _BUILTIN_RULES]
        if source_sqlite:
            rules.append(RowCountMismatchRule(source_sqlite))

    report = ValidationReport()
    for rule in rules:
        results = rule.check(target_sqlite)
        for r in results:
            if not r.passed:
                if r.severity == 'error':
                    report.total_errors += 1
                else:
                    report.total_warnings += 1
        report.results.extend(results)

    return report


def print_validation_report(report: ValidationReport) -> None:
    """Вывести отчёт проверки в консоль."""
    total = report.total_errors + report.total_warnings
    if total == 0:
        print('✅ Все проверки пройдены')
        return
    print(f'{"="*60}')
    print(f'Результат проверки: {report.total_errors} ошибок, '
          f'{report.total_warnings} предупреждений')
    print(f'{"="*60}')
    for r in report.results:
        if r.passed:
            continue
        icon = '❌' if r.severity == 'error' else '⚠️'
        where = f'{r.object_name}.{r.field}' if r.field else r.object_name
        print(f'{icon} [{r.rule}] {where}')
        if r.expected:
            print(f'   expected={r.expected} actual={r.actual}')
        elif r.actual:
            print(f'   {r.actual}')
    print(f'{"="*60}')
