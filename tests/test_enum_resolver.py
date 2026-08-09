"""Тесты разрешения перечислений в xlsx-мосте (enum_resolver)."""
from __future__ import annotations

from pathlib import Path

import pytest

from onec_converter.enum_resolver import (
    EnumResolver,
    extract_enum_values,
    guid_str_to_ref,
)
from onec_converter.fake_1cd import (
    FixtureField,
    FixtureTable,
    encode_row,
    write_fake_1cd,
)
from onec_converter.source_8x_file import Database1CD, decode_field, read_metadata
from onec_converter.write_8x import create_1cd

# эталон: CONFIG-guid с layout перестановки -> 16 байт ссылки (проверено реальной базой)
GUID_CFG = 'c97c4519-705c-4a3a-8251-7a57d5160dbd'
GUID_REF = bytes.fromhex('82517a57d5160dbd4a3a705cc97c4519')


def test_guid_str_to_ref_conversion():
    assert guid_str_to_ref(GUID_CFG) == GUID_REF


def test_guid_str_to_ref_invalid():
    assert guid_str_to_ref('') == b'\x00' * 16
    assert guid_str_to_ref('xxxx') == b'\x00' * 16
    assert guid_str_to_ref('c9..-x') == b'\x00' * 16


BRACKET = '''{1,
{5,
{0,
{0,
{0,0,57f238d7-94db-4bde-bb29-30080fb398f4},"ПеречислениеТест",
{1,"ru","Перечисление Тест"},"Перечисление Тест"}
},0},
2,
{bee0a08c-07eb-40c0-8544-5c364c171465,2,
{
{0,
{0,
{0,0,c97c4519-705c-4a3a-8251-7a57d5160dbd},"Мужской",
{1,"ru","Мужской"},"Мужской"}
},0},
{
{0,
{0,
{0,0,d2298b5e-5fac-4c73-b1af-21e21ef6c6fc},"Женский",
{1,"ru","Женский"},"Женский"}
},0}
}
}}'''


def test_extract_enum_values_from_config():
    class FakeDB:
        def __init__(self, content):
            self._content = content

        def config_get(self, name):
            return self._content

    db = FakeDB(BRACKET.encode('utf-8'))
    out = extract_enum_values(db, {'guid': 'any'})
    assert out == [('Мужской', 'Мужской'), ('Женский', 'Женский')]
    # пустой CONFIG не роняет
    assert extract_enum_values(FakeDB(b''), {'guid': 'any'}) == []
    assert extract_enum_values(FakeDB(None), {'guid': 'any'}) == []
    assert extract_enum_values(FakeDB(b'{not valid'), {'guid': 'any'}) == []
    assert extract_enum_values(FakeDB(BRACKET.encode('utf-8')), {'guid': ''}) == []


def _enum_base(tmp_path: Path, values: list[bytes]) -> Path:
    """База с таблицей _ENUM11: строки _IDRREF = values."""
    fields = [
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_ENUMORDER', 'N', length=6),
    ]
    rows = [encode_row(fields, {'_IDRREF': v}) for v in values]
    create_1cd(tmp_path / '1Cv8.1CD',
               [FixtureTable('_ENUM11', fields=fields, rows=rows)])
    return tmp_path


def test_enum_resolver_by_synonym_and_ref(tmp_path: Path):
    ref_a = guid_str_to_ref(GUID_CFG)
    ref_b = guid_str_to_ref('d2298b5e-5fac-4c73-b1af-21e21ef6c6fc')
    _enum_base(tmp_path, [ref_a, ref_b])
    meta = {'table': '_ENUM11', 'guid': 'x'}
    with Database1CD(tmp_path / '1Cv8.1CD') as db:
        r = EnumResolver(db, meta,
                         values=[('Мужской', 'Мужской'),
                                 ('Женский', 'Женский')])
        assert r.by_synonym('мужской') == ref_a       # регистр-фри
        assert r.by_synonym('  женский ') == ref_b    # лишние пробелы
        assert r.by_synonym('НетТакогоЗначения') == b'\x00' * 16
        assert r.by_ref(ref_a) == 'Мужской'
        assert r.by_ref(ref_b) == 'Женский'
        assert r.by_ref(b'\x01' * 16) == ''


def test_enum_resolver_normalizes_by_name_when_no_synonym(tmp_path: Path):
    ref = guid_str_to_ref(GUID_CFG)
    _enum_base(tmp_path, [ref])
    meta = {'table': '_ENUM11', 'guid': 'x'}
    # внутреннее имя как fallback (без ru-синонима)
    with Database1CD(tmp_path / '1Cv8.1CD') as db:
        r = EnumResolver(db, meta, values=[('МУЖСКОЙ_ПОЛ', '')])
        assert r.by_synonym('мужской пол') == ref


BASE_81 = Path(__file__).resolve().parents[1] / '1C_8.1' / '1Cv8.1CD'


@pytest.mark.integration
def test_extract_enum_values_from_real_base():
    """Integration: извлечение значений/резолвинг на реальной базе приёмника."""
    if not BASE_81.is_file():
        pytest.skip('нет реальной базы 1C_8.1')
    md = read_metadata(BASE_81)
    target = None
    for meta in md['objects']:
        if meta.get('kind') == 'Перечисление' and meta.get('table') == '_ENUM101':
            target = meta
            break
    assert target is not None
    with Database1CD(BASE_81) as db:
        vals = extract_enum_values(db, target)
        assert len(vals) == 35
        t = db.tables['_ENUM101']
        rows = [row[1:17] for row in db.table_rows(t) if row[:1] != b'\x01']
        assert len(rows) == len(vals)
        r = EnumResolver(db, target)
        for i, (name, syn) in enumerate(vals):
            assert r.by_synonym(syn or name) == rows[i]
            assert r.by_ref(rows[i]) == (syn or name)


def _receiver_with_enum(tmp_path: Path) -> Path:
    """База со справочником `_REFERENCE7` (+ колонка-ссылка на перечисление)
    и таблицей перечисления `_ENUM11`."""
    ref_a = guid_str_to_ref(GUID_CFG)
    ref_b = guid_str_to_ref('d2298b5e-5fac-4c73-b1af-21e21ef6c6fc')
    enum_fields = [FixtureField('_IDRREF', 'B', length=16),
                   FixtureField('_ENUMORDER', 'N', length=6)]
    cat_fields = [
        FixtureField('_IDRREF', 'B', length=16),
        FixtureField('_VERSION', 'RV', length=16),
        FixtureField('_MARKED', 'L'),
        FixtureField('_ISMETADATA', 'L'),
        FixtureField('_CODE', 'NC', length=9),
        FixtureField('_DESCRIPTION', 'NVC', length=40),
        FixtureField('_Fld100', 'B', length=16),  # значение перечисления
    ]
    enum_rows = [encode_row(enum_fields, {'_IDRREF': r}) for r in (ref_a, ref_b)]
    cat_rows = [encode_row(cat_fields, {})]  # служебная строка для append
    target = tmp_path / 'target'
    target.mkdir()
    (target / '1Cv8.1CD').write_bytes(write_fake_1cd(
        tmp_path / 'base.1CD',
        [FixtureTable('_ENUM11', fields=enum_fields, rows=enum_rows),
         FixtureTable('_REFERENCE7', fields=cat_fields, rows=cat_rows)]))
    return target


CAT_META = {
    'kind': 'Справочник', 'name': 'Сотрудники', 'table': '_REFERENCE7',
    'attributes': [
        {'name': 'Код', 'field': '_CODE', 'type': 'string', 'length': 9,
         'precision': 0},
        {'name': 'Наименование', 'field': '_DESCRIPTION', 'type': 'string',
         'length': 40, 'precision': 0},
        {'name': '_Fld100', 'field': '_Fld100', 'type': 'ref', 'length': 16,
         'precision': 0},
    ],
}

ENUM_META = {
    'kind': 'Перечисление', 'name': 'Пол', 'table': '_ENUM11', 'guid': 'x',
}


def test_import_enum_column_resolves_to_idrref(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """E2E: колонка-перечисление в мосте резолвится в _IDRREF приёмника."""
    from onec_converter.bridge_format import (
        MODE_CATALOG,
        BridgeConfig,
        ColumnSpec,
        write_bridge,
    )
    from onec_converter.epf_load import import_bridge
    from onec_converter.typify import KIND_REF, KIND_STRING, TypeSpec

    monkeypatch.setattr('onec_converter.epf_load.read_metadata',
                        lambda p: {'objects': [dict(CAT_META), dict(ENUM_META)]})
    monkeypatch.setattr(
        'onec_converter.enum_resolver.extract_enum_values',
        lambda db, meta: [('Мужской', 'Мужской'), ('Женский', 'Женский')])
    target = _receiver_with_enum(tmp_path)
    ref_a = guid_str_to_ref(GUID_CFG)

    cols = [
        ColumnSpec(flag=1, attr='Код', search=True,
                   type_spec=TypeSpec(kinds=(KIND_STRING,), str_length=9),
                   mode='Устанавливать', default='', lookup='Код',
                   owner_ref='', type_ref='', type_elem='', col_num=1),
        ColumnSpec(flag=1, attr='_Fld100', search=False,
                   type_spec=TypeSpec(kinds=(KIND_REF,),
                                      ref_type='Перечисление.Пол'),
                   mode='Устанавливать', default='', lookup='',
                   owner_ref='', type_ref='', type_elem='', col_num=2),
    ]
    cfg = BridgeConfig(mode=MODE_CATALOG, obj_fullname='Справочник.Сотрудники',
                       first_data_row=2, columns=cols)
    bridge = tmp_path / 'b.xlsx'
    write_bridge(bridge, cfg, [['00001', 'Мужской'], ['00002', 'Женский']])

    rep = import_bridge(bridge, target, workdir=tmp_path / 'wd')
    assert rep['ok'] and rep['created'] == 2 and rep['errors'] == []
    with Database1CD(Path(rep['copy_path'])) as db:
        t = db.tables['_REFERENCE7']
        rows = [r for r in db.table_rows(t) if r[:1] != b'\x01'
                and r[t.fields['_IDRREF'].offset:
                      t.fields['_IDRREF'].offset + 16] != b'\x00' * 16]
        assert len(rows) == 2
        code_size = t.fields['_CODE'].size
        codes = sorted(
            decode_field(t.fields['_CODE'],
                         r[t.fields['_CODE'].offset:
                           t.fields['_CODE'].offset + code_size])
            for r in rows)
        assert codes == ['00001', '00002']
        flds = {decode_field(t.fields['_CODE'],
                             r[t.fields['_CODE'].offset:
                               t.fields['_CODE'].offset + code_size]):
                r[t.fields['_Fld100'].offset:
                  t.fields['_Fld100'].offset + 16] for r in rows}
        assert flds['00001'] == ref_a
        assert flds['00002'] != b'\x00' * 16

