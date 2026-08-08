# Spec: core

## Purpose
Довести Фазу 29 до конца: карта команд (29.1), export-kd3 и подтверждение
search_schema (29.2). Версия 0.14.0.

## Acceptance criteria
- [x] docs/commands-map.md: CLI (20 подкоманд) + MCP (13 тулов), входы/выходы,
      поток inspect→extract→map→transform→load→verify, next-цепочки, общие
      флаги; секция «Взаимосвязи» (реестр CLI 20/20, аргументы согласованы,
      дубли MCP удалены в 29.1)
- [x] Реестр CLI согласован: парсеры (add_parser) = handlers (registry),
      20/20, мёртвых команд нет; commands-map не содержит дублей
- [x] kd3_export.py: export_kd3(rules_path, out_file) — TOON rules.json ->
      XML КД3-стиля (DataContainer/Rules/Rule/Attributes/Attribute/
      EnumMappings/Mapping); Kd3Error: нет файла / не JSON / неверная схема
      (version != 1)
- [x] CLI export-kd3: --rules (обязателен), --out; rc=1 с сообщением
- [x] search_schema: поиск по синониму документа, по имени таблицы регистра,
      по реквизиту документа — покрыто тестами
- [x] Тесты +6: согласованность реестра, commands-map, export-kd3
      (структура/out-файл/ошибки), search_schema
- [x] README export-kd3; CHANGELOG 0.14.0; план Фаза 29 ✅ (все чекбоксы
      29.1 и 29.2)
- [x] Ворота: pytest (все, gates.sh на E:), conformance, ruff, mypy strict,
      vitest — зелёные; релиз 0.14.0 на всех площадках
