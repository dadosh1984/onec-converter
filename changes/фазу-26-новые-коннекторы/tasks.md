# Tasks — Фаза 26: Новые коннекторы (техжурнал + релиз конфигурации)

Ворота: mypy strict, ruff, pytest (в `E:\test` через gates.sh), vitest.
Версия 0.11.0 (SemVer монотонно, не номер фазы). Релиз: TestPyPI → PyPI → GitHub.

## source_techlog.py
- [x] [fact] `parse_techlog_line`: строка техжурнала -> событие (ts ISO, duration_ms,
      level, process, direction, context, event, level2, fields); мусор -> None
- [x] [fact] `TechLog.iter_events(process, event, level_min, tail)` — фильтры;
      *.log/*.lgp, utf-8+replace, устойчивость к CRLF
- [x] [fact] `TechLog.read_events(...)`: count/events/files, out_file JSON,
      INFO-событие audit (techlog); TechLogError для несуществующего каталога

## fetch_config.py
- [x] [fact] `parse_configuration_xml`: XML-выгрузка (Configuration.xml) ->
      {objects: [kind, name, uuid]}; FetchConfigError (нет каталога/файла,
      повреждённый XML; двоичные .cf — честная ошибка с подсказкой)
- [x] [fact] `fetch_config(source, out_file)`: обёртка, JSON-запись,
      INFO-событие audit (fetch-config)

## CLI
- [x] [fact] подкоманда `techlog` (--source-dir/--process/--event/--level-min/
      --tail/--out) + `fetch-config` (--source/--out), регистрация в handlers

## Тесты и доки
- [x] [fact] тесты: парсинг/мусор, фильтры (process/event/level_min/tail),
      out_file, ошибки; XML-релиз, .cf-ошибка, audit (+11)
- [x] [fact] docs/format-8x.md — «Техжурнал 1С (спайк)»; README — источники
      techlog/fetch-config; CHANGELOG 0.11.0; план Фаза 26 ✅

## Верификация
- [x] [assumption] pytest (все), conformance, ruff, mypy, vitest — зелёные
- [x] [assumption] релиз 0.11.0: TestPyPI → PyPI → GitHub Release
