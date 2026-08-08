# Proposal — фаза-34-0-17

**Goal:** Фаза 34 (0.17.0) — Производительность ядра onec-converter: (1) table_stats: добавить быстрый режим оценки числа строк по размеру страницы/длине строки из метаданных без физического чтения данных (len(data)//row_length с кешем); base_health sample доступен; (2) mmap: использовать mmap для чтения 1Cv8.1CD в source_8x_file где безопасно (крупные page-read), сохраняя фолов.к бэкенд; не ломать существующие тесты чтения; (3) load_direct/пересборка индексов: в write_8x.пересобрать index_page из метаданных при записи (убрать warning «индексы не пересобираются») либо документировать/тест на перенос index_page blob из источника; (4) parallel_extract: option --workers для extract (ThreadPoolExecutor по независимым справочникам); тест детерминизма. Приоритет: диагностируем mmap риск — если небезопасно на Windows, фиксируем только table_stats + индексы + parallel. Честно оценки.

- Platform: тесты в E:\test через gates.sh; версия 0.17.0; mypy только src
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фаза-11-новая-порция:forge:537c39f668a9, фаза-11-новая-порция:forge:409e2a92d172, запись-индексов-b-tree:forge:6759ab959277, mcp-python-1-7:forge:232cb52a8565, mcp-python-1-7:forge:64a0dea04a25
