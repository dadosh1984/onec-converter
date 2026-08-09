# Дизайн — Фаза 58 (0.41.0): производительность и ворота

## Сделано
- H1: `gates.sh all` теперь включает `run_benchmark`.
- H2: контракт-тест — тулы CLI `mcp` (cmd_mcp) идентичны тулам mcp_server.
- H4: тест единого источника COVERAGE_MODULES — gates.sh читает имена из
  pyproject, не захардкожены в скрипте.
- H5: hypothesis fuzz audit hash-цепочки — запись→чтение→verify цела,
  любая мутация записи разрывает цепочку (deadline щадящий 3s, чтобы не
  флапать на загруженном CI).

## Нет-оп (реализовано ранее)
- D4: `read_metadata` уже кеширует в mem-LRU (Фаза 49 U39) + disk кеш;
  ai-map/ai-explain переиспользуют автоматически — доп. работы не нужно.

## Верификация
- ruff/mypy green; pytest 543 (+5 Фаза 58); benchmark ok (gates all);
  vitest не затронут.
