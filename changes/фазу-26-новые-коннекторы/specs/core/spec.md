# Spec: core

## Purpose
Новые коннекторы-источники (Фаза 26): техжурнал 1С как источник событий
(`source_techlog.py`) и релиз конфигурации из XML-выгрузки как источник
метаданных (`fetch_config.py`), с CLI-подкомандами, аудитом, тестами и
доками. Версия 0.11.0.

## Acceptance criteria
- [x] `parse_techlog_line`: строка техжурнала -> событие (ts ISO UTC, duration_ms,
      level, process, direction, context, event, level2, fields); мусор -> None;
      устойчивость к CRLF и любой кодировке (utf-8 + replace)
- [x] `TechLog.iter_events(process, event, level_min, tail)`: файлы *.log/*.lgp,
      фильтры по процессу (подстрока), событию, минимальному уровню, tail
- [x] `TechLog.read_events(...)`: {ok, count, events, files}, опциональный
      out_file (JSON), INFO-событие аудита techlog; TechLogError при
      несуществующем каталоге
- [x] `parse_configuration_xml`: XML-выгрузка (Configuration.xml) ->
      {ok, objects: [kind, name, uuid], total}; FetchConfigError: нет каталога /
      нет Configuration.xml / повреждённый XML / двоичный .cf (подсказка об
      XML-выгрузке)
- [x] `fetch_config(source, out_file)`: обёртка + JSON-запись + INFO-событие
      аудита fetch-config
- [x] CLI: подкоманды `techlog` (--source-dir/--process/--event/--level-min/
      --tail/--out) и `fetch-config` (--source/--out); rc=0 + JSON в stdout,
      ошибки -> rc=1 в stderr
- [x] Тесты: парсинг строки и мусора, фильтры (event/process/level_min/tail),
      out_file, ошибки каталога; XML-релиз (3 объекта), .cf-ошибка, audit
- [x] docs/format-8x.md «Техжурнал 1С (спайк)»; README — techlog/fetch-config;
      CHANGELOG 0.11.0; план Фаза 26 ✅
- [x] Ворота: pytest (все, gates.sh на E:), conformance, ruff, mypy strict,
      vitest — зелёные; релиз 0.11.0 на всех площадках
