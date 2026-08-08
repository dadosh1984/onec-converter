"""Фаза 29: аудит команд — карта, взаимосвязи, export-kd3, search_schema."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

META_WIDE = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'synonym': 'Банковские реквизиты',
     'table': '_REFERENCE7', 'ref_num': 7,
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC'}]},
    {'kind': 'Документ', 'name': 'Продажа', 'synonym': 'Реализация товаров',
     'table': '_DOCUMENT56', 'ref_num': 56,
     'attributes': [{'name': 'Номер', 'field': '_NUMBER', 'type': 'NC'},
                    {'name': 'Дата', 'field': '_DATE_TIME', 'type': 'DT'}]},
    {'kind': 'РегистрСведений', 'name': 'КурсыВалют', 'synonym': '',
     'table': '_INFO10', 'ref_num': 10,
     'attributes': [{'name': 'Валюта', 'field': '_Fld22', 'type': 'B'}]},
]}


# ---- 29.1: согласованность реестра команд ----
def test_cli_registry_consistent():
    src = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    subs = set(re.findall(r"add_parser\('([^']+)'", src))
    handlers = {m[0] for m in re.findall(r"'([^']+)': (cmd_\w+)", src)}
    assert len(subs) == len(handlers) == 20  # нет «мёртвых» команд
    assert subs == handlers  # каждая подкоманда имеет обработчик и наоборот
    assert 'load' in subs and 'transform' in subs and 'export-kd3' in subs


def test_commands_map_exists():
    doc = Path('docs/commands-map.md').read_text(encoding='utf-8')
    assert 'CLI (20)' in doc and 'MCP (13 тулов)' in doc
    assert 'export-kd3' in doc and 'base_health' in doc
    assert 'query_table' not in doc  # дубль удалён в 29.1


# ---- 29.2: export-kd3 ----
RULES = {'version': 1, 'enums': {'Мужской': 'M', 'Женский': 'F'},
         'objects': [{'source': 'Справочник.Банки',
                      'target': 'Справочник.Банки',
                      'attributes': {'Код': 'Код',
                                     'Наименование': 'Наименование'}}]}


def test_export_kd3(tmp_path: Path):
    from onec_converter.kd3_export import export_kd3

    rf = tmp_path / 'rules.json'
    rf.write_text(json.dumps(RULES), encoding='utf-8')
    rep = export_kd3(rf)
    assert rep['ok'] and rep['rules'] == 1 and rep['enums'] == 2
    root = ET.fromstring(rep['xml'])
    assert root.tag == 'DataContainer'
    rule = root.find('Rules/Rule')
    assert rule is not None
    assert rule.get('source') == 'Справочник.Банки'
    attrs = {a.get('source'): a.get('target')
             for a in rule.findall('Attributes/Attribute')}
    assert attrs == {'Код': 'Код', 'Наименование': 'Наименование'}
    m = root.findall('EnumMappings/Mapping')
    assert len(m) == 2 and m[0].get('target') == 'M'


def test_export_kd3_out_file(tmp_path: Path):
    from onec_converter.kd3_export import export_kd3

    rf = tmp_path / 'rules.json'
    rf.write_text(json.dumps(RULES), encoding='utf-8')
    out = tmp_path / 'kd3.xml'
    export_kd3(rf, out_file=str(out))
    assert out.is_file()
    assert 'DataContainer' in out.read_text(encoding='utf-8')


def test_export_kd3_errors(tmp_path: Path):
    from onec_converter.kd3_export import Kd3Error, export_kd3

    with pytest.raises(Kd3Error, match='нет файла'):
        export_kd3(tmp_path / 'нет.json')
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')
    with pytest.raises(Kd3Error, match='не JSON'):
        export_kd3(bad)
    wrong = tmp_path / 'wrong.json'
    wrong.write_text(json.dumps({'version': 9, 'objects': []}),
                     encoding='utf-8')
    with pytest.raises(Kd3Error, match='схема'):
        export_kd3(wrong)


# ---- 29.2: search_schema — документы/регистры/синонимы ----
def test_search_schema_by_synonym(tmp_path, monkeypatch):
    from onec_converter import mcp_server as m

    src = tmp_path / 'src'
    src.mkdir()
    (src / '1Cv8.1CD').write_bytes(b'x')  # проверка файла до read_metadata
    monkeypatch.setattr('onec_converter.source_8x_file.read_metadata',
                        lambda p: META_WIDE)
    # по синониму документа
    rep = json.loads(m.search_schema(str(src), 'реализация'))
    assert rep['ok']
    names = {o['name'] for o in rep['objects']}
    assert 'Продажа' in names
    # по имени таблицы регистра
    rep2 = json.loads(m.search_schema(str(src), '_INFO10'))
    assert [o['kind'] for o in rep2['objects']] == ['РегистрСведений']
    # по реквизиту документа
    rep3 = json.loads(m.search_schema(str(src), 'Номер'))
    assert any(f['object'] == 'Документ.Продажа' for f in rep3['fields'])
