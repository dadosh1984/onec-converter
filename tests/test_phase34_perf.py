"""Фаза 34: производительность ядра — индексы (index_rebuilder), parallel extract."""
from __future__ import annotations

from pathlib import Path

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd


def _db(tmp_path: Path) -> tuple[Path, Path]:
    from onec_converter.fake_1cd import encode_row
    F1 = [FixtureField('_VERSION', 'RV', length=16),
          FixtureField('_IDRREF', 'B', length=16),
          FixtureField('_CODE', 'NC', length=9),
          FixtureField('_DESCRIPTION', 'NVC', length=40)]
    src = tmp_path / 'src'
    src.mkdir()
    cd = src / '1Cv8.1CD'
    cd.write_bytes(build_fake_1cd([
        FixtureTable('_REFERENCE1', fields=F1, rows=[
            encode_row(F1, {'_IDRREF': b'\x01' * 16, '_CODE': f'{i:05d}',
                             '_DESCRIPTION': f'Item {i}'})
            for i in range(4)]),
        FixtureTable('_REFERENCE2', fields=[
            FixtureField('_VERSION', 'RV', length=16)]),
    ]))
    return src, cd


# ---- index_rebuilder ----
def test_index_rebuilder_creates_script(tmp_path: Path, monkeypatch):
    from onec_converter.index_rebuilder import build_repair_script

    monkeypatch.setattr('onec_converter.index_rebuilder.shutil.which',
                        lambda x: None)
    _src, cd = _db(tmp_path)
    tgt = tmp_path / 'tgt'
    tgt.mkdir()
    (tgt / '1Cv8.1CD').write_bytes(cd.read_bytes())
    rep = build_repair_script(tgt)
    assert rep['ok'] is True
    assert rep['tool_used'] in ('1cv8', 'chdbfl')
    sp = Path(rep['script'])
    assert sp.is_file()
    text = sp.read_text(encoding='utf-8')
    assert '1Cv8.1CD' in text  # скрипт указывает на базу приёмника


def test_index_rebuilder_missing_db(tmp_path: Path):
    from onec_converter.index_rebuilder import IndexRepairError, build_repair_script

    empty = tmp_path / 'empty'
    empty.mkdir()
    try:
        build_repair_script(empty)
        assert False, 'должна быть ошибка'
    except IndexRepairError:
        pass


# ---- parallel extract детерминизм ----
def _make_cli(tmp_path: Path) -> dict:
    import onec_converter.cli as cm
    spec = cm._extract_8x(str(tmp_path), 0, [], workers=1)
    return {'cli': cm, 'seq': spec}


def test_extract_workers_deterministic(tmp_path: Path):
    import onec_converter.cli as cm
    src, _cd = _db(tmp_path)
    seq = cm._extract_8x(str(src), 0, [], workers=1)
    par = cm._extract_8x(str(src), 0, [], workers=3)
    assert seq == par  # порядок и содержимое идентичны
    assert len(seq) >= 1
    types = {o['type'] for o in seq}
    assert 'Таблица._REFERENCE1' in types


def test_extract_limit_parallel(tmp_path: Path):
    import onec_converter.cli as cm
    src, _cd = _db(tmp_path)
    lim = cm._extract_8x(str(src), 3, [], workers=3)
    assert len(lim) == 3


def test_extract_cli_has_workers_flag():

    cli = Path('src/onec_converter/cli.py').read_text(encoding='utf-8')
    assert "'--workers'" in cli
