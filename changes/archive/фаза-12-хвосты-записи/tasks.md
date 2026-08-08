# Tasks — фаза-12-хвосты-записи

Закрыть ограничения Фазы 10 в `write_8x.py`: fat_level 1 (объекты > 8 МБ),
защита от записи в открытую ИБ, риск индексов. Запись — только на копиях.

- [x] [spike] Индексы 1CD: формат index-объекта (B-tree, сигнатура `1c fd`,
      index_page из каталога) и риск append без пересборки индексов →
      раздел «Индексы и запись» в docs/format-8x.md
- [x] [fact] `write_8x.py`: `_read_object`/`_write_object_header` — поддержка
      fat_level 1 (заголовок → indirect-страницы → данные); `append_records`
      для fat_level 1 (дописывание страниц данных и indirect при росте,
      WriteError при превышении слотов FAT — нужен fat_level 2)
- [x] [fact] `write_8x.py`: защита — LockError (WriteError) при открытой ИБ
      (рядом 1Cv8.1CL или 1Cv8tmp*) и предупреждение (warnings) при записи
      в таблицу с индексами (index_page != 0); unit-тесты
- [x] [fact] Unit-тесты fat_level 1 на синтетике: объект собран вручную
      низкоуровневыми функциями → append → парсер читает без потерь;
      WriteError при превышении слотов
- [x] [assumption] Интеграционный тест: append в fat_level 1 таблицу на
      КОПИИ реальной базы 8.1 (tmp) → чтение парсером, размеры сходятся
- [x] [assumption] README/docs: обновлённые ограничения записи (fat_level 1
      поддержан; индексы не пересобираются — риск; блокировка открытой ИБ)

Ворота: pytest (вкл. integration), mypy strict, ruff, vitest (Orion shield).
Python 3.11+, Windows, реальные базы read-only. Только stdlib.
