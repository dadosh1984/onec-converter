"""Фаза 26: fetch-config — релиз конфигурации (XML-выгрузка) как источник."""
from __future__ import annotations

import json

import pytest

from onec_converter.fetch_config import FetchConfigError, fetch_config, parse_configuration_xml

CFG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.2/uap/configuration" version="2.4">
  <Configuration uuid="c0ffee00-0000-0000-0000-000000000001">
    <Properties>
      <Name>ТестоваяКонфигурация</Name>
    </Properties>
    <ChildObjects>
      <Справочник uuid="11111111-1111-1111-1111-111111111111">
        <Properties><Name>Банки</Name></Properties>
      </Справочник>
      <Документ uuid="22222222-2222-2222-2222-222222222222">
        <Properties><Name>Продажа</Name></Properties>
      </Документ>
      <РегистрСведений uuid="33333333-3333-3333-3333-333333333333">
        <Properties><Name>КурсыВалют</Name></Properties>
      </РегистрСведений>
    </ChildObjects>
  </Configuration>
</MetaDataObject>
"""


def _make_release(tmp_path, content: str = CFG_XML):
    rel = tmp_path / 'release'
    rel.mkdir()
    (rel / 'Configuration.xml').write_text(content, encoding='utf-8')
    return rel


def test_parse_release(tmp_path):
    rel = _make_release(tmp_path)
    rep = parse_configuration_xml(rel)
    assert rep['ok'] and rep['total'] == 3
    kinds = [o['kind'] for o in rep['objects']]
    assert kinds == ['Справочник', 'Документ', 'РегистрСведений']
    banks = rep['objects'][0]
    assert banks['name'] == 'Банки'
    assert banks['uuid'].startswith('11111111')


def test_fetch_config_out_file(tmp_path):
    rel = _make_release(tmp_path)
    out = tmp_path / 'meta.json'
    fetch_config(rel, out_file=str(out))
    assert out.is_file()
    saved = json.loads(out.read_text(encoding='utf-8'))
    assert saved['total'] == 3


def test_fetch_config_errors(tmp_path):
    with pytest.raises(FetchConfigError):
        fetch_config(tmp_path / 'нет-такого')
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(FetchConfigError, match='Configuration.xml'):
        fetch_config(empty)
    # двоичный .cf не поддерживается — честная ошибка с подсказкой
    (empty / 'Release.cf').write_bytes(b'\x1c\xf8\xe1\xf1' + b'\x00' * 64)
    with pytest.raises(FetchConfigError, match='XML-выгрузка'):
        fetch_config(empty)


def test_fetch_config_bad_xml(tmp_path):
    rel = _make_release(tmp_path, content='<MetaDataObject><unclosed>')
    with pytest.raises(FetchConfigError, match='повреждён'):
        fetch_config(rel)


def test_fetch_config_audit(tmp_path):
    from onec_converter.audit import read_audit, set_audit

    set_audit(tmp_path / 'audit.jsonl')
    rel = _make_release(tmp_path)
    fetch_config(rel)
    recs = read_audit(tmp_path / 'audit.jsonl')
    assert recs[0]['operation'] == 'fetch-config' and recs[0]['result'] == 'ok'
    set_audit(None)
