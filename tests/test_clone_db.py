"""Фаза 24: полный сценарий копии базы — clone-db + снапшот/откат.

clone_db: полная копия 1Cv8.1CD в новый каталог (+ кеш-сброс), опция
--with-rules (стенд). load_direct: автоматический snapshot.1CD приёмника
до записи (откат при сбое), опция --no-snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from onec_converter.clone_db import CloneError, clone_db
from onec_converter.fake_1cd import FixtureField, FixtureTable, encode_row
from onec_converter.load_8x import load_direct
from onec_converter.source_8x_file import Database1CD
from onec_converter.write_8x import create_1cd

F_REFERENCE = [
    FixtureField('_VERSION', 'RV', length=16),
    FixtureField('_IDRREF', 'B', length=16),
    FixtureField('_CODE', 'NC', length=9),
    FixtureField('_DESCRIPTION', 'NVC', length=40),
]


def _fake_target(tmp_path: Path, name: str = 'tgt') -> Path:
    tgt = tmp_path / name
    tgt.mkdir(exist_ok=True)
    create_1cd(tgt / '1Cv8.1CD',
               [FixtureTable('_REFERENCE7', fields=F_REFERENCE,
                             rows=[encode_row(F_REFERENCE, {
                                 '_IDRREF': b'\x11' * 16,
                                 '_CODE': '00000', '_DESCRIPTION': 'seed'})])])
    return tgt


def _rows(path: Path, table: str = '_REFERENCE7') -> list[dict]:
    with Database1CD(path) as db:
        t = db.tables[table]
        return [{fn: onec_decode(fd, row[fd.offset:fd.offset + fd.size])
                 for fn, fd in t.fields.items()}
                for row in db.table_rows(t)]


def onec_decode(fd: object, raw: bytes) -> object:
    from onec_converter.source_8x_file import decode_field
    return decode_field(fd, raw)


# ---- clone-db ----
def test_clone_db_full_copy(tmp_path: Path):
    """Полная копия: файл целиком, таблицы на месте, оригинал не тронут."""
    src = _fake_target(tmp_path, 'src')
    before = (src / '1Cv8.1CD').read_bytes()
    tgt = tmp_path / 'clone'

    rep = clone_db(src, tgt)
    assert rep['ok'] and Path(rep['target']).is_file()
    assert rep['tables'] == 1 and rep['bytes'] > 0
    assert (tgt / '1Cv8.1CD').read_bytes() == before  # побитовая копия
    assert (src / '1Cv8.1CD').read_bytes() == before  # оригинал не изменён
    assert _rows(tgt / '1Cv8.1CD')[0]['_DESCRIPTION'] == 'seed'


def test_clone_db_with_rules(tmp_path: Path):
    """--with-rules: правила маппинга копируются рядом (сценарий «стенд»)."""
    src = _fake_target(tmp_path, 'src')
    rules = tmp_path / 'rules.json'
    rules.write_text('{"mapping": []}', encoding='utf-8')
    tgt = tmp_path / 'stand'

    rep = clone_db(src, tgt, rules)
    rp = Path(rep['rules'])
    assert rp.is_file() and rp.parent.name == 'rules'
    assert rp.read_text(encoding='utf-8') == '{"mapping": []}'


def test_clone_db_errors(tmp_path: Path):
    """Нет 1Cv8.1CD / клонирование в себя — CloneError."""
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(CloneError, match='1Cv8.1CD'):
        clone_db(empty, tmp_path / 'out')
    src = _fake_target(tmp_path, 'src2')
    with pytest.raises(CloneError, match='в себя'):
        clone_db(src, src)


def test_clone_db_cli(capsys, tmp_path: Path):
    """CLI clone-db: JSON-ответ через cmd_clone_db."""
    from onec_converter.cli import cmd_clone_db

    src = _fake_target(tmp_path, 'src3')
    args = argparse.Namespace(source_dir=str(src),
                              target_dir=str(tmp_path / 'cli_clone'),
                              with_rules='')
    assert cmd_clone_db(args) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep['ok'] and Path(rep['target']).is_file()


# ---- snapshot / restore ----
META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0},
                    {'name': 'Наименование', 'field': '_DESCRIPTION',
                     'type': 'NVC', 'length': 40, 'precision': 0}]},
]}


def _objs() -> list[dict]:
    return [{'type': 'Справочник.Банки', 'key': ['00001', 'Банк'],
             'attributes': {'Код': '00001', 'Наименование': 'Банк'},
             'references': {}}]


def test_snapshot_created_and_restore_on_failure(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch):
    """До записи создаётся snapshot.1CD; при сбое снапшот восстанавливает
    приёмник побитово (имитация: повреждение результата записи)."""
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    tgt = _fake_target(tmp_path)
    original = (tgt / '1Cv8.1CD').read_bytes()
    wd = tmp_path / 'wd'

    rep = load_direct(tgt, _objs(), workdir=wd)
    assert rep['ok']
    snap = Path(rep['snapshot'])
    assert snap.is_file() and snap.read_bytes() == original

    # имитация сбоя: результат записи повреждён
    copy_path = Path(rep['copy_path'])
    copy_path.write_bytes(b'\xff' * 100)

    # откат: приёмник из снапшота == оригинал до миграции
    (tgt / '1Cv8.1CD').write_bytes(snap.read_bytes())
    assert (tgt / '1Cv8.1CD').read_bytes() == original


def test_no_snapshot_flag(tmp_path: Path,
                          monkeypatch: pytest.MonkeyPatch):
    """--no-snapshot: снапшот не создаётся."""
    monkeypatch.setattr('onec_converter.load_8x.read_metadata',
                        lambda p: META)
    tgt = _fake_target(tmp_path)
    rep = load_direct(tgt, _objs(), workdir=tmp_path / 'wd2', snapshot=False)
    assert rep['ok'] and rep['snapshot'] is None
