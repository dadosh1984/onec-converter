# Tasks — фаза-8-xlsx-отчёты

XLSX-отчёты структур и размеров таблиц. `xlsx_report.py` уже содержит
`build_report` (отчёт по данным: лист на тип объекта) — добавляем отчёты
структуры (diff compare_structures) и размеров (table_sizes).

- [ ] [fact] `xlsx_report.py`: функция отчёта структуры —
      листы «Только в источнике» / «Только в приёмнике» / «Расхождения типов»
      (объект, поле, тип_источника, тип_приёмника) на основе вывода
      compare_structures
- [ ] [assumption] MCP-тул `structure_report(source_dir, target_dir, out_file)`:
      формирует XLSX, возвращает путь и сводку counts
- [ ] [assumption] MCP-тул `table_sizes_report(source_dir, out_file, top_n)`:
      лист «Таблицы», сортировка по байтам, топ-N
- [ ] [fact] Unit-тесты XLSX: openpyxl читает файл обратно — проверка
      листов, заголовков, строк, кириллицы, пустых структур
- [ ] [assumption] Интеграционная проверка на реальных базах 1C_8.1/1C_8.3
      (read-only): отчёт формируется, размеры совпадают с table_sizes

Ворота: pytest, mypy strict, ruff, vitest (Orion shield). XLSX-файлы —
в .gitignore (отчёты не коммитим). Реальные базы — read-only.
