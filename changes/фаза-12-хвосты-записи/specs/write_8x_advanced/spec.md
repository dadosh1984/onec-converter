# Spec: write_8x_advanced

## Purpose

Фаза 12: закрыть ограничения Фазы 10 в `src/onec_converter/write_8x.py`
(запись только на копиях, только stdlib): поддержка fat_level 1
(объекты > 8 МБ), защита от записи в открытую ИБ, документирование риска
индексов.

## Capabilities

### fat_level 1 (write_8x.py)

- `_read_object`/`_write_object_header` поддерживают fat_level 1:
  заголовок-объект (сигнатура `1c fd`, длина uint64 @16) → FAT-список
  страниц-указателей (indirect) → страницы данных.
- `append_records` для fat_level 1: дописывание страниц данных и indirect
  при росте; WriteError при превышении слотов FAT заголовка (нужен
  fat_level 2 — не поддерживается).

### Защита записи (write_8x.py)

- LockError (подкласс WriteError) при открытой ИБ: рядом с `1Cv8.1CD`
  существует `1Cv8.1CL` или `1Cv8tmp*`.
- Предупреждение (warnings.warn) при записи в таблицу с индексами
  (index_page != 0) — индексы не пересобираются.

## Acceptance criteria

- [ ] fat_level 1: append → парсер читает без потерь (unit на синтетике,
      integration на КОПИИ реальной 8.1, 4 такие таблицы)
- [ ] LockError при наличии 1Cv8.1CL; warning при index_page != 0
- [ ] WriteError при превышении слотов FAT (fat_level 2)
- [ ] docs/format-8x.md («Индексы и запись», обновлённые ограничения),
      README (раздел «Прямая запись»)
- [ ] Ворота: pytest (вкл. integration) / mypy strict / ruff / vitest
