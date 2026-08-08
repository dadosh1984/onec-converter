# Tasks — Фаза 29.2: селективный перенос по разделам

Ворота: mypy strict, ruff, pytest, vitest. Релиз 0.6.0.

## Фильтр
- [x] [fact] `objects_filter.py`: ObjectSpec + parse_objects (Раздел.Имя,
      группы Раздел.*, Таблица._REFERENCE3; ошибки формата) + selects()
- [x] [fact] CLI `extract --objects`: проброс в 7.7 (Справочник.<id>) и 8.x
      (read_metadata: kind+имя → таблицы; Таблица.* без метаданных; без
      --objects — все данные, совместимость)
- [x] [fact] MCP `step_extract(objects="")` — селективный перенос

## Тесты
- [x] [fact] unit: парсер/матчер (точно/группы/Таблица/ошибки)
- [x] [fact] CLI 8.x на fake-базе: Таблица._REFERENCE3; неверный формат → rc=1
- [x] [fact] реальная база 8.1 (read-only): маппинг групп Справочник.*
- [x] [fact] MCP: step_extract с objects (группа/точный/нет раздела)

## Доки
- [x] [fact] README (селективный перенос), CHANGELOG 0.6.0, план — задача ✅

## Верификация
- [x] [assumption] pytest (все), ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.6.0: TestPyPI → PyPI → GitHub Release
