"""Фаза 28: DX — BDD-сценарии, sonar-report, OpenAPI-спека."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from onec_converter.sonar_report import SonarReportError, one_issue, sonar_report

R = ['src/onec_converter/__init__.py', 'src/onec_converter/audit.py']


# ---- sonar-report ----
def test_one_issue_mapping():
    it = one_issue('RUF022', 'src/a.py', 3, 'сообщение')
    assert it == {'ruleId': 'RU022', 'severity': 'MINOR',
                  'component': 'src/a.py', 'line': 3, 'message': 'сообщение'}
    f_err = one_issue('F401', 'src/b.py', 1, 'unused')
    assert f_err['ruleId'] == 'F401' and f_err['severity'] == 'MAJOR'


def test_sonar_report_json_on_target():
    # линтуем себя: ruff на чистом файле -> total >= 0, формат json
    rep = sonar_report('src/onec_converter/__init__.py', fmt='json',
                       ruff_cmd=['python', '-m', 'ruff', 'check'])
    assert rep['ok'] and rep['format'] == 'json'
    body = json.loads(rep['body'])
    assert isinstance(body, list)
    assert rep['total'] == len(body)
    for it in body:
        assert 'ruleId' in it and 'severity' in it and 'component' in it


def test_sonar_report_xml_valid():
    rep = sonar_report('src/onec_converter/__init__.py', fmt='xml',
                       ruff_cmd=['python', '-m', 'ruff', 'check'])
    root = ET.fromstring(rep['body'])  # валидный XML
    assert root.tag == 'issues'
    assert all(c.tag == 'issue' for c in root)


def test_sonar_report_bad_format():
    with pytest.raises(SonarReportError, match='формат'):
        sonar_report('src', fmt='yaml')


def test_sonar_report_missing_ruff():
    with pytest.raises(SonarReportError, match='ruff'):
        sonar_report('src', fmt='json', ruff_cmd=['definitely-not-ruff-xyz'])


# ---- OpenAPI-генератор ----
def test_gen_openapi(tmp_path, monkeypatch):
    import scripts.gen_openapi as g

    # прямо: сбор путей/обработчиков из реального кода
    eps = g.collect_endpoints()
    assert {e['path'] for e in eps} >= {'/metadata', '/load'}
    hnd = g.collect_handlers()
    assert 'ЗаписьДанных' in hnd and 'МетаданныеИБ' in hnd

    yaml_text = g.build_openapi(eps, hnd)
    assert yaml_text.startswith('openapi: 3.0.3')
    assert '/metadata' in yaml_text and 'operationId: МетаданныеИБ' in yaml_text
    assert 'operationId: ЗаписьДанных' in yaml_text
    assert 'X-API-Key' in yaml_text


def test_openapi_yaml_file_valid():
    # docs/openapi.yaml — валидный YAML со спека
    import yaml

    with open('docs/openapi.yaml', encoding='utf-8') as f:
        doc = yaml.safe_load(f)
    assert doc['openapi'].startswith('3.')
    paths = doc['paths']
    assert '/metadata' in paths and '/load' in paths
    assert paths['/metadata']['get']['operationId'] == 'МетаданныеИБ'
    assert paths['/load']['post']['operationId'] == 'ЗаписьДанных'
    assert 'ApiKeyAuth' in doc['components']['securitySchemes']
