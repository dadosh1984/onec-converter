# Tasks — Фаза 29 (довести): карта команд, export-kd3, search_schema

Ворота: mypy strict (src), ruff, pytest (E:\test, gates.sh), vitest.
Версия 0.14.0. Релиз: TestPyPI → PyPI → GitHub.

## 29.1 Инвентаризация
- [x] [fact] docs/commands-map.md: CLI (20) + MCP (13), входы/выходы, поток
      данных, next-цепочки, общие флаги; проверка взаимосвязей
- [x] [fact] тест: реестр CLI согласован (парсеры = handlers, 20/20, нет
      мёртвых); commands-map без дублей

## 29.2 Внедрение навыков
- [x] [fact] kd3_export.py: export_kd3(rules_path, out_file) — TOON →
      XML КД3-стиля (DataContainer/Rules/Attribute/EnumMappings); Kd3Error
      (нет файла/не JSON/неверная схема)
- [x] [fact] CLI export-kd3: --rules/--out
- [x] [fact] search_schema: тесты на документы/регистры и поиск по синонимам

## Тесты и доки
- [x] [fact] тесты +6: реестр, commands-map, export-kd3 (структура/файл/
      ошибки), search_schema
- [x] [fact] README export-kd3; CHANGELOG 0.14.0; план Фаза 29 ✅
      (все чекбоксы 29.1/29.2)

## Верификация
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.14.0: TestPyPI → PyPI → GitHub Release
