"""Sonar-отчёт по lint: `sonar-report` (Фаза 28, идея acc-export/stebi).

Генерация отчёта ruff в формате SonarQube «Generic Issue Import» (XML) или
JSON — для CI-интеграции: запуск `python -m ruff check <target> --output-format=json`
и конвертация записей в issues. Правила отображаются без префикса
(например RUF022 -> RU022), severity: F/E -> MAJOR, прочее -> MINOR.
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RULES_FILE = Path(__file__).resolve().parents[2] / 'pyproject.toml'


class SonarReportError(Exception):
    """Ошибка генерации sonar-отчёта."""


def _severity(code: str) -> str:
    return 'MAJOR' if code[:1] in ('F', 'E') else 'MINOR'


def one_issue(code: str, file: str, line: int, message: str) -> dict[str, Any]:
    """Одна запись sonar generic issue: RUF-правила -> RU<номер>."""
    if code.startswith('RUF') and code[3:].isdigit():
        rule = f'RU{code[3:]}'
    else:
        rule = code
    return {'ruleId': rule, 'severity': _severity(code),
            'component': file, 'line': line, 'message': message}


def _run_ruff(target: str, ruff_cmd: list[str]) -> list[dict[str, Any]]:
    """Запуск ruff с JSON-выводом; пустой результат при отсутствии ruff."""
    cmd = ruff_cmd + [target, '--output-format=json',
                      f'--config={RULES_FILE}']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             check=False).stdout
    except OSError as exc:
        raise SonarReportError(f'не удалось запустить ruff: {exc}') from exc
    try:
        raw = json.loads(out or '[]')
    except ValueError as exc:
        raise SonarReportError(f'неверный вывод ruff: {exc}') from exc
    issues: list[dict[str, Any]] = []
    for item in raw:
        loc = (item.get('location') or {}).get('row') or 1
        issues.append(one_issue(item.get('code') or 'UNKNOWN',
                                item.get('filename') or target,
                                int(loc), item.get('message') or ''))
    return issues


def _to_xml(issues: list[dict[str, Any]]) -> str:
    root = ET.Element('issues')
    for it in issues:
        ET.SubElement(root, 'issue',
                      {k: str(v) for k, v in it.items()})
    ET.indent(root)
    return ET.tostring(root, encoding='unicode',
                       xml_declaration=True)


def sonar_report(target: str = 'src', fmt: str = 'xml',
                 ruff_cmd: list[str] | None = None) -> dict[str, Any]:
    """Отчёт ruff в sonar-формате: {ok, issues, xml|json, total}.

    target — каталог/файл линтинга (по умолчанию src); fmt — 'xml'
    (Generic Issue Import) или 'json'."""
    if fmt not in ('xml', 'json'):
        raise SonarReportError(f'неизвестный формат: {fmt}')
    issues = _run_ruff(target, ruff_cmd or [sys.executable, '-m', 'ruff',
                                            'check'])
    body = _to_xml(issues) if fmt == 'xml' else json.dumps(
        issues, ensure_ascii=False, indent=1)
    return {'ok': True, 'total': len(issues), 'format': fmt,
            'issues': issues, 'body': body}
