# Design — фаза-8-xlsx-отчёты

## Overview

Закрыть обещанный в C2 (Фаза 6) XLSX-отчёт структуры и добавить отчёт
размеров таблиц. Отчёты — в openpyxl (уже в зависимостях), файлы в tmp/
или каталоге пользователя (в .gitignore, не коммитим).

## Модули

- `src/onec_converter/xlsx_report.py` — добавить:
  - `build_structure_report(diff, out_path)` — листы «Только в источнике»
    (колонки: объект), «Только в приёмнике» (объект), «Расхождения типов»
    (объект, поле, тип_источника, тип_приёмника); diff — словарь как в
    выводе MCP-тула compare_structures (only_source/only_target/type_mismatch);
  - `build_sizes_report(sizes, out_path, top_n=50)` — лист «Таблицы»
    (таблица, строки, байты), сортировка по байтам, топ-N.
- `src/onec_converter/mcp_server.py` — тулы:
  - `structure_report(source_dir, target_dir, out_file)` → {ok, path, counts};
  - `table_sizes_report(source_dir, out_file, top_n)` → {ok, path, tables}.
- `tests/test_xlsx_report.py` — unit-тесты: openpyxl читает файл обратно
  (листы, заголовки, строки), кириллица, пустые структуры (diff пуст →
  листы с заголовками и 0 строк), top_n.

## Решения

- Переиспользуем внутренности compare_structures: вынесем чистую функцию
  `diff_structures(ms, mt)` (или вызываем логику сравнения напрямую),
  чтобы и JSON-тул, и XLSX-тул строили отчёт из одних данных.
- Пустые структуры: лист создаётся с заголовками и 0 строк (openpyxl
  позволяет) — «ничего не найдено» видно по сводке counts.
- Кириллица: openpyxl пишет UTF-8 по умолчанию; заголовки листов —
  короткие латинские/русские имена без запрещённых символов.

## Assumptions

- [ ] [fact] build_structure_report (листы only_source/only_target/type_mismatch)
- [ ] [assumption] MCP-тул structure_report → {path, counts}
- [ ] [assumption] MCP-тул table_sizes_report → {path, tables}
- [ ] [fact] Unit-тесты XLSX (openpyxl read-back, кириллица, пустые)
- [ ] [assumption] Интеграционная проверка на 1C_8.1/1C_8.3 (read-only)

## Verification

- [x] pytest (все тесты, включая новые unit XLSX)
- [x] mypy src (strict)
- [x] ruff check src tests
- [x] npx vitest run (Orion shield)
