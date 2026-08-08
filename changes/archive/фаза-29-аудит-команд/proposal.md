# Proposal — довести-фазу-29-аудит

**Goal:** Довести Фазу 29 (Аудит команд и внедрение навыков) до конца в onec-converter: (1) docs/commands-map.md — карта команд CLI (20) + MCP (13), входы/выходы, поток данных, next-цепочки, проверка взаимосвязей (реестр CLI 20/20 совпадает, аргументы --source-dir/--out/--format согласованы); (2) export-kd3 — модуль kd3_export.py (export_kd3(rules_path, out_file): правила TOON → XML в стиле КД3 DataContainer/Rules/Attribute/EnumMappings; Kd3Error: нет файла/не JSON/неверная схема) + CLI подкоманда export-kd3 --rules --out; (3) search_schema — подтвердить тестами расширение на документы/регистры и поиск по синонимам; (4) тесты +6: согласованность реестра команд (парсеры↔handlers), commands-map существует и без дублей, export-kd3 (XML-структура/out-файл/ошибки), search_schema по синониму/таблице/реквизиту; (5) README export-kd3, CHANGELOG 0.14.0, план Фаза 29 ✅ (все чекбоксы 29.1 и 29.2); релиз 0.14.0.

- Platform: тесты в E:\test через gates.sh; версия 0.14.0; mypy только src
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-24-полный-сценарий:forge:1b6dbaa2498b, фазу-24-полный-сценарий:forge:873ac75a95fb, фазу-25-audit-логирование:forge:919b9b494e28
