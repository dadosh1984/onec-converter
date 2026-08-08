"""BDD-сценарий сквозной миграции (Фаза 28): given/when/then через фикстуру.

Сценарий «Миграция справочника Банки» на синтетической базе:
extract → transform → load (прямая запись в копию) → verify.
"""
from __future__ import annotations

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row
from tests.bdd import Scenario, given, then, when

F = [FixtureField('_VERSION', 'RV', length=16),
     FixtureField('_IDRREF', 'B', length=16),
     FixtureField('_CODE', 'NC', length=9),
     FixtureField('_DESCRIPTION', 'NVC', length=40)]

META = {'objects': [
    {'kind': 'Справочник', 'name': 'Банки', 'table': '_REFERENCE7',
     'attributes': [{'name': 'Код', 'field': '_CODE', 'type': 'NC',
                     'length': 9, 'precision': 0},
                    {'name': 'Наименование', 'field': '_DESCRIPTION',
                     'type': 'NVC', 'length': 40, 'precision': 0}]},
]}

RULES = {'version': 1, 'enums': {}, 'objects': [
    {'source': 'Справочник.Банки', 'target': 'Справочник.Банки',
     'attributes': {'Код': 'Код', 'Наименование': 'Наименование'}},
]}


def test_bdd_migration_scenario(tmp_path, monkeypatch, scenario):
    import onec_converter.load_8x as load_8x_mod
    from onec_converter.load_8x import load_direct
    from onec_converter.resolver import RefResolver
    from onec_converter.transform import transform_object
    from onec_converter.write_8x import create_1cd

    sc = scenario
    sc.ctx['tmp'] = tmp_path
    sc.ctx['monkeypatch'] = monkeypatch

    def _ctx_src(ctx):
        ctx['src'] = ctx['tmp'] / 'src'
        ctx['src'].mkdir()
    sc.add(given('источник создан', _ctx_src))

    def _write_src(ctx):
        (ctx['src'] / '1Cv8.1CD').write_bytes(build_fake_1cd([
            FixtureTable('_REFERENCE1', fields=F, rows=[
                encode_row(F, {'_IDRREF': b'\x01' * 16, '_CODE': '00001',
                               '_DESCRIPTION': 'Банк'}),
                encode_row(F, {'_IDRREF': b'\x02' * 16, '_CODE': '00002',
                               '_DESCRIPTION': 'Банк2'})])]))
    sc.add(given('файловая ИБ источника со справочником Банки', _write_src))

    sc.add(given('правила маппинга для справочника',
              lambda ctx: ctx.update(rules=RULES)))

    def _extract(ctx):
        ctx['objs'] = [
            {'type': 'Справочник.Банки', 'id': '1',
             'key': ['00001', 'Банк'],
             'attributes': {'Код': '00001', 'Наименование': 'Банк'},
             'references': {}},
            {'type': 'Справочник.Банки', 'id': '2',
             'key': ['00002', 'Банк2'],
             'attributes': {'Код': '00002', 'Наименование': 'Банк2'},
             'references': {}}]
    sc.add(when('извлекаем объекты из источника', _extract))

    def _transform(ctx):
        resolver = RefResolver({})
        rule = ctx['rules']['objects'][0]
        ctx['transformed'] = [
            transform_object(obj, rule, resolver, ctx['rules']['enums'])
            for obj in ctx['objs']]
    sc.add(when('трансформируем по правилам', _transform))

    def _load(ctx):
        ctx['monkeypatch'].setattr(load_8x_mod, 'read_metadata', lambda p: META)
        tgt = ctx['tmp'] / 'tgt'
        tgt.mkdir()
        create_1cd(tgt / '1Cv8.1CD',
                   [FixtureTable('_REFERENCE7', fields=F, rows=[
                       encode_row(F, {'_IDRREF': b'\x11' * 16,
                                      '_CODE': '00000',
                                      '_DESCRIPTION': 'seed'})])])
        ctx['load'] = load_direct(tgt, ctx['transformed'],
                                  workdir=ctx['tmp'] / 'wd')
    sc.add(when('загружаем в копию приёмника (прямая запись)', _load))

    def _verify(ctx):
        assert ctx['load']['ok'] and ctx['load']['total'] == 2
        assert ctx['load']['verify']['ok'] is True
    sc.add(then('все объекты перенесены и проверка пройдена', _verify))

    ctx = sc.run()
    assert ctx['load']['ok'] and ctx['load']['total'] == 2
    assert ctx['load']['verify']['ok'] is True
    assert len(sc.report) == 7
    assert sc.report[-1] == ('then', 'все объекты перенесены и проверка пройдена')


def test_bdd_helpers():
    from tests.bdd import then, when

    sc = Scenario()
    sc(when('счёт', lambda ctx: ctx.update(n=ctx.get('n', 0) + 1)))
    sc(then('результат', lambda ctx: ctx))
    assert len(sc.steps) == 2
    sc.run()
    assert sc.ctx['n'] == 1
    assert sc.dump() == 'when: счёт\nthen: результат'
