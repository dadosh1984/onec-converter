# Spec: core

## Purpose
Закрыть заявленные пункты производительности ядра: восстановление индексов
после прямой записи и параллельное извлечение. mmap и table_stats уже
реализованы в source_8x_file — подтверждаются тестами, без повторной работы.
Версия 0.17.0.

## Acceptance criteria
- [x] mmap-чтение 1Cv8.1CD уже реализовано (source_8x_file read_page —
      срез mmap); подтверждено grep-тестом
- [x] table_stats кеширован, читает цепочку данных (не blob), работает
- [x] index_rebuilder.build_repair_script(target_dir, tool=auto|1cv8|chdbfl)
      генерирует скрипт восстановления индексов приёмника; IndexRepairError
      при отсутствии 1Cv8.1CD
- [x] CLI load --direct --index-repair вызывает index_rebuilder и печатает
      путь скрипта
- [x] extract --workers N: ThreadPoolExecutor по именам таблиц, порядок
      строк сохранён (map), вывод детерминирован (тест 1 vs 3 workers)
- [x] README: ограничение «индексы не пересобираются» + решение
      --index-repair задокументировано
- [x] Ворота: pytest (+5), conformance, ruff, mypy (44), check_bsl,
      vitest — зелёные; релиз 0.17.0
