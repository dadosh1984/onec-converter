# Spec: core

## Purpose
Реализовать Фазу 12 «Хвосты прямой записи в 1CD»: закрыть ограничения Фазы 10 в src/onec_converter/write_8x.py (только stdlib, запись только на копиях). Задачи: (1) spike — формат индекс-объектов 1CD (B-tree, сигнатура 1cfd, index_page из каталога) и риск append без пересборки индексов → раздел «Индексы и запись» в docs/format-8x.md; (2) поддержать fat_level 1 в _read_object/_write_object_header и append_records (объекты > 8 МБ: заголовок → indirect-страницы → страницы данных; в реальной 1C_8.1 есть 4 такие таблицы) с unit-тестами на синтетическом fat_level 1 объекте; (3) защита записи: отказ (WriteError/LockError) при открытой ИБ (файл 1Cv8.1CL существует) и предупреждение при записи в таблицу с индексами (index_page != 0); (4) интеграционный тест: append в fat_level 1 таблицу на КОПИИ реальной базы 8.1 (tmp) → чтение парсером без потерь, размеры сходятся; (5) README/docs: обновить ограничения записи (fat_level 1 поддержан, индексы — риск, блокировка открытой ИБ). Ворота: pytest (вкл. integration), mypy strict, ruff, vitest (Orion shield). Python 3.11+, Windows, реальные базы read-only (запись только в tmp-копии).

## Acceptance criteria
- [ ] Placeholder — refine during implementation
