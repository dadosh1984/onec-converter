# Tasks — фаза-10-прямая-запись

Прямая запись в 1CD 8.3 без HTTP-расширения. Парсер read-only есть
(source_8x_file: Database1CD — заголовок, каталог, FAT level 0/1, цепочки
блоков, BINARYDATA/SERIALIZEDDATA) и фикстуры fake_1cd (FixtureTable,
FixtureField, encode_row, build_fake_1cd). Запись — только на копиях.

- [x] [spike] Формат 1CD 8.3 на запись: root-объект, каталог таблиц,
      FAT level 0/1, цепочки блоков, SERIALIZEDDATA; что нужно для создания
      новой базы и добавления записей (обновление размеров таблицы и FAT);
      риски целостности → раздел «Запись» в docs/format-8x.md
- [x] [assumption] `write_8x.py`: `create_1cd(path, tables)` — новая пустая
      база по структуре приёмника (таблицы, поля, индексы) — переиспользует
      layout fake_1cd; unit-тест: база читается Database1CD
- [x] [assumption] `write_8x.py`: `append_records(db, table, rows)` —
      добавление строк в конец таблицы: новые страницы данных, обновление
      FAT level 0/1, длины объекта и total_pages в заголовке
- [x] [fact] Unit-тесты: записанные строки декодируются парсером обратно
      без потерь (все типы полей из FixtureField)
- [x] [assumption] Интеграционный тест на КОПИИ 8.3-базы (tmp): копия
      исходника → append тестовых записей → чтение парсером, размеры сходятся
- [x] [assumption] README/docs: раздел «Прямая запись» + ограничения
      (только копии, не оригиналы)

Ворота: pytest, mypy strict, ruff, vitest (Orion shield). Python 3.11+,
Windows, реальные базы read-only. Только stdlib, без новых зависимостей.
