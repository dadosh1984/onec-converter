# Proposal — фазу-26-новые-коннекторы

**Goal:** Реализовать Фазу 26 Новые коннекторы в onec-converter: (1) source_techlog.py — техжурнал 1С как источник событий (каталог логов *.log/*.lgp; парсер строки: время/длительность/уровень/процесс/направленность/контекст/событие/поля; фильтры process/event/level_min/tail, out_file JSON; TechLogError; INFO-событие в audit); (2) fetch_config.py — fetch-config: релиз конфигурации из XML-выгрузки 1С (Configuration.xml) как источник метаданных {objects: kind/name/uuid}; FetchConfigError; честная ошибка для двоичных .cf с подсказкой; INFO-событие в audit; (3) CLI подкоманды techlog и fetch-config; (4) тесты +11: парсинг строки/мусор, фильтры, out_file, ошибки, XML-релиз, audit; (5) docs/format-8x.md раздел «Техжурнал 1С (спайк)», README источники, CHANGELOG 0.11.0, план Фаза 26 ✅; релиз 0.11.0.

- Platform: тесты в E:\test через gates.sh; версия 0.11.0 (не номер фазы)
- Constraints: compact
- Budget: compact
- **Lessons applied (v0.12):** фазу-23-conformance-тесты:forge:753265ca3073, фазу-25-audit-логирование:forge:7c216dc57da7, фазу-25-audit-логирование:forge:919b9b494e28, фазу-24-полный-сценарий:forge:1b6dbaa2498b, запись-индексов-b-tree:forge:6182cf6f8ced
