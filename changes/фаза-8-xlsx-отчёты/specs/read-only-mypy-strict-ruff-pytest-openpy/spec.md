# Spec: read-only-mypy-strict-ruff-pytest-openpy

## Purpose
Фаза 8: XLSX-отчёты структур и размеров таблиц для MCP-сервера onec_converter (перенос между ИБ 1С, парсер 1Cv8.1CD). Закрыть обещанный в C2 (Фаза 6) XLSX-отчёт и добавить отчёт размеров. Уже есть src/onec_converter/xlsx_report.py с build_report (отчёт по данным: лист на тип объекта) и MCP-тулы compare_structures (JSON-diff only_source/only_target/type_mismatch) и table_sizes (размеры таблиц). Задачи: (1) xlsx_report.py — функция отчёта структуры: листы «Только в источнике» / «Только в приёмнике» / «Расхождения типов» (объект, поле, тип_источника, тип_приёмника) на основе вывода compare_structures; (2) MCP-тул structure_report(source_dir, target_dir, out_file): формирует XLSX, возвращает путь и сводку counts; (3) MCP-тул table_sizes_report(source_dir, out_file, top_n): лист «Таблицы», сортировка по байтам, топ-N; (4) unit-тесты XLSX: openpyxl читает файл обратно — проверка листов, заголовков, строк, кириллицы, пустых структур (когда diff пуст); (5) интеграционная проверка на реальных базах 1C_8.1/1C_8.3 (read-only): отчёт формируется, размеры совпадают с table_sizes. Ворота: pytest, mypy strict, ruff, vitest (Orion shield). Python 3.11+, Windows.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
