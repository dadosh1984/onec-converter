# Spec: write_1cd

## Purpose

Фаза 10: прямая запись в 1CD 8.3 без HTTP-расширения. Загрузка в приёмник
8.x напрямую в файл базы. Парсер read-only есть (source_8x_file: Database1CD),
фикстуры — fake_1cd (FixtureTable/FixtureField/build_fake_1cd). Запись — только
на копиях (никогда на оригиналах). Только stdlib, без новых зависимостей.

## Capabilities

### create_1cd (write_8x.py)

- Новая пустая база 1CD по структуре приёмника: таблицы, поля, индексы —
  переиспользует layout build_fake_1cd (заголовок 1CDBMSV8/8.3.8.0, root-объект
  с каталогом в blob-цепочках, объекты данных таблиц).
- Возвращает путь созданного файла.

### append_records (write_8x.py)

- Добавление строк в конец таблицы существующей базы (data_page != 0):
  новые страницы данных, обновление FAT level 0/1 и длины объекта,
  total_pages в заголовке файла.
- Таблица без объекта данных (data_page == 0) — WriteError с объяснением.
- Ошибки: WriteError (нет таблицы, длина строк не кратна row_length).

## Acceptance criteria

- [ ] create_1cd: файл читается Database1CD, таблицы/поля совпадают
- [ ] append_records: строки декодируются парсером обратно без потерь
      (все типы полей FixtureField)
- [ ] Интеграция: копия 8.3-базы (tmp) → append → чтение, размеры сходятся
- [ ] README/docs: раздел «Прямая запись» + ограничения (только копии)
- [ ] Ворота: pytest / mypy strict / ruff / vitest — без ошибок
