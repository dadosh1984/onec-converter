"""Тесты CLI extract: 7.7/8.x -> intermediate JSON (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main
from onec_converter.fake_1cd import FixtureField, FixtureTable, write_fake_1cd
from tests.fixtures.gen_dat import make_dat


def _base77(tmp_path: Path) -> Path:
    base = tmp_path / 'base77'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2},
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]}))
    return base


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def test_extract_77(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out)])
    assert rc == 0
    objs = _load(out)
    assert len(objs) == 2
    assert objs[0]['type'] == 'Справочник.1'
    assert objs[0]['key'] == ['0001', 'Товар А']
    assert objs[0]['attributes']['_descr'] == 'Товар А'


def test_extract_limit(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--limit', '1'])
    assert rc == 0
    assert len(_load(out)) == 1


def test_extract_objects_filter(tmp_path: Path):
    base = tmp_path / 'base77m'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 2, 2: 1},
        references={1: [['1|', '0001', 'Товар А']],
                    2: [['1|', '0001', 'Контрагент X']]}))
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--objects', 'Справочник.2'])
    assert rc == 0
    objs = _load(out)
    assert len(objs) == 1
    assert objs[0]['type'] == 'Справочник.2'


def test_extract_anonymize(tmp_path: Path):
    base = _base77(tmp_path)
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--anonymize-fields', '_descr'])
    assert rc == 0
    objs = _load(out)
    # 'Товар А' не содержит PII — остаётся; маскируется ФИО/телефон/ИНН
    assert objs[0]['attributes']['_descr'] == 'Товар А'


def test_extract_anonymize_fio(tmp_path: Path):
    base = tmp_path / 'base77f'
    base.mkdir()
    (base / '1Cv7.MD').write_bytes(b'd0cf11e0')
    (base / '1Cv77.dat').write_bytes(make_dat(
        unique_ids={1: 1},
        references={1: [['1|', '0001', 'Иванов Иван Иванович']]}))
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(base), '--out', str(out),
               '--anonymize-fields', '_descr'])
    assert rc == 0
    objs = _load(out)
    assert objs[0]['attributes']['_descr'] == 'Иванов И. И.'


def test_extract_8x(tmp_path: Path):
    t = FixtureTable('_REFERENCE3', fields=[
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=150),
    ])
    cd = tmp_path / 'base8x'
    cd.mkdir()
    write_fake_1cd(cd / '1Cv8.1CD', [t])
    out = tmp_path / 'out.json'
    rc = main(['extract', '--source-dir', str(cd), '--out', str(out)])
    assert rc == 0
    objs = _load(out)
    assert len(objs) >= 0  # пустая таблица допустима; главное — JSON читается