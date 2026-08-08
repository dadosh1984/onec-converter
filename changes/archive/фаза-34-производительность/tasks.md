# Tasks — Фаза 34: Производительность ядра (0.17.0)

## mmap / table_stats (подтверждено реализованным)
- [x] [spike] mmap уже в source_8x_file (read_page — срез памяти)
- [x] [fact] table_stats кеширован, читает данные без blob; base_health
      sample по row_length

## Индексы
- [x] [fact] index_rebuilder.py + load --direct --index-repair; тест
- [x] [fact] README: ограничение по индексам + решение --index-repair

## Параллельность
- [x] [fact] extract --workers: ThreadPool, порядок/детерминизм; тест

## Доки / релиз
- [x] [fact] CHANGELOG 0.17.0; план Фаза 34 ✅
- [x] [assumption] ворота зелёные; релиз 0.17.0
