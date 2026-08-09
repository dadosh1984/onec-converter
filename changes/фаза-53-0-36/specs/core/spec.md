# Spec: core

## Purpose
Финальная фаза раунда 5: довести продукт до востребованного набора
CLI-инструментов (отчёты, шаблоны, диагностика, статистика) и
документации для практического применения (формат 8.x, пример миграции,
облачные среды). Версия 0.36.0.

## Acceptance criteria
- [x] export-xlsx (U11), map --init (U12), doctor --fix (U13),
      mcp (U15), stats (U16); реестр CLI 28 -> 31
- [x] README матрица команд (U51); docs/format-8x.md (U52);
      docs/recipes/бухгалтерия-77-в-83.md (U53);
      docs/recipes/облачные-среды.md (U54)
- [x] pii-report (RU/UZ) — уже покрывал gdpr; нет-оп (U55)
- [x] list-tables SQL — в бэклог (U56); TOON schema_version — уже (U62)
- [x] ruff/mypy/pytest/conformance зелёные; релиз 0.36.0 (последний раунда 5)
