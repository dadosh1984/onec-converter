"""RED-тесты формата xlsx-моста (аналог макета «МакетСохраненияНастроек» .epf)."""
from __future__ import annotations

from pathlib import Path

from onec_converter.bridge_format import (
    MODE_CATALOG,
    MODE_REGISTER,
    MODE_TABLE,
    BridgeConfig,
    ColumnSpec,
    read_bridge,
    write_bridge,
)
from onec_converter.typify import KIND_NUMBER, KIND_STRING, TypeSpec


def _cfg() -> BridgeConfig:
    return BridgeConfig(
        version='1.2',
        mode=MODE_CATALOG,
        obj_fullname='Справочник.Контрагенты',
        no_new=False,
        replace=True,
        manual_cols=True,
        first_data_row=2,
        columns=[
            ColumnSpec(flag=True, attr='Код', search=True,
                       type_spec=TypeSpec(kinds=(KIND_NUMBER,)),
                       mode='Устанавливать', default='', lookup='Код',
                       owner_ref='', type_ref='', type_elem=0, col_num=1),
            ColumnSpec(flag=True, attr='Наименование', search=False,
                       type_spec=TypeSpec(kinds=(KIND_STRING,)),
                       mode='Устанавливать', default='', lookup='',
                       owner_ref='', type_ref='', type_elem=0, col_num=2),
        ],
        before_write='def hook(obj): pass',
        after_write='',
        after_add_row='',
    )


def test_write_read_roundtrip(tmp_path: Path):
    cfg = _cfg()
    rows = [[1, 'ООО Ромашка'], [2, 'ООО Поле']]
    path = tmp_path / 'bridge.xlsx'
    write_bridge(path, cfg, rows)
    cfg2, rows2 = read_bridge(path)
    assert cfg2.version == cfg.version
    assert cfg2.mode == MODE_CATALOG
    assert cfg2.obj_fullname == 'Справочник.Контрагенты'
    assert cfg2.no_new is False and cfg2.replace is True
    assert cfg2.manual_cols is True and cfg2.first_data_row == 2
    assert len(cfg2.columns) == 2
    c = cfg2.columns[0]
    assert c.flag and c.attr == 'Код' and c.search
    assert c.type_spec.kinds == (KIND_NUMBER,)
    assert c.lookup == 'Код' and c.col_num == 1
    assert cfg2.before_write == 'def hook(obj): pass'
    assert rows2 == rows


def test_mode_register_roundtrip(tmp_path: Path):
    cfg = _cfg()
    cfg.mode = MODE_REGISTER
    cfg.obj_fullname = 'РегистрСведений.ОстаткиТоваров'
    path = tmp_path / 'r.xlsx'
    write_bridge(path, cfg, [])
    cfg2, _ = read_bridge(path)
    assert cfg2.mode == MODE_REGISTER
    assert cfg2.obj_fullname == 'РегистрСведений.ОстаткиТоваров'


def test_mode_table_roundtrip(tmp_path: Path):
    cfg = _cfg()
    cfg.mode = MODE_TABLE
    path = tmp_path / 't.xlsx'
    write_bridge(path, cfg, [['x']])
    cfg2, rows = read_bridge(path)
    assert cfg2.mode == MODE_TABLE
    assert rows == [['x']]


def test_computed_column_roundtrip(tmp_path: Path):
    cfg = _cfg()
    cfg.columns[1].mode = 'Вычислять'
    cfg.columns[1].lookup = 'ТекущиеДанные.Код + "!"'
    path = tmp_path / 'c.xlsx'
    write_bridge(path, cfg, [])
    cfg2, _ = read_bridge(path)
    assert cfg2.columns[1].mode == 'Вычислять'
    assert cfg2.columns[1].lookup == 'ТекущиеДанные.Код + "!"'


def test_empty_bridge_read(tmp_path: Path):
    path = tmp_path / 'e.xlsx'
    write_bridge(path, _cfg(), [])
    _, rows = read_bridge(path)
    assert rows == []


def test_manual_columns_numbering(tmp_path: Path):
    cfg = _cfg()
    cfg.columns[0].col_num = 5
    cfg.columns[1].col_num = 6
    path = tmp_path / 'm.xlsx'
    write_bridge(path, cfg, [[1, 2]])
    cfg2, rows = read_bridge(path)
    assert cfg2.columns[0].col_num == 5
    assert rows[0][4] == 1 and rows[0][5] == 2
