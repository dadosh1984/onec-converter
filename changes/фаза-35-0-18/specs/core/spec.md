# Spec: core

## Purpose
Обеспечить перенос регистров сведений/накопления и автоматический маппинг
перечислений по именам. Подтвердить, что регистры пишутся существующей
механикой, добавить enum_mapper и рецепт. Версия 0.18.0.

## Acceptance criteria
- [x] Регистры _InfoRg/_AccumRg структурно пишутся append_records:
      тест записи двух строк в таблицу _InfoRg100 на fake-базе (3 строки
      после добавления) + повторное чтение
- [x] enum_mapper.py: normalize_enum_name (регистр/пробел-независимо),
      build_enum_map (только совпадающие имена), map_enum_value (str и int)
- [x] transform: применение enum-маппинга (имя как строка и dict имя->имя)
      покрыто тестами
- [x] docs/recipes/перенос-остатков-регистры.md — руководствоextract/
      rules/load + перечисления
- [x] Ворота: pytest (+7), conformance, ruff, mypy (45), check_bsl,
      vitest — зелёные; релиз 0.18.0
