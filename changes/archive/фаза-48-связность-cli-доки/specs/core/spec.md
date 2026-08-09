# Spec: core

## Purpose
Закрыть дрейф «документировано ↔ выполнимо»: выставить verify, cache trim,
audit export-csv, rules-diff в CLI; контракт-тест команд ловит дрейф
навсегда. Версия 0.31.0.

## Acceptance criteria
- [x] `verify --input --target [--objects] [--json]`: rc=0 при полном
      совпадении (ключ+атрибуты), rc=1 при расхождениях; отчёт
      {ok, total_source, total_target, matched, missing, mismatched};
      рецепт полного цикла использует реальную команду (extract из
      приёмника -> verify)
- [x] `cache trim --max-bytes/--ttl` — LRU-эвикция из CLI, отчёт
      {removed, bytes, files}
- [x] `audit --csv-out <file>` — отфильтрованный журнал в CSV
      (utf-8-sig, колонки ts/level/operation/obj/result/guid/rule)
- [x] `rules-diff --a --b [--json]` — added/removed/changed по объектам
- [x] Контракт-тест: каждая команда docs/commands-map.md существует в
      CLI (add_parser) или MCP (@visible_tool)
- [x] Реестр CLI 26 -> 28; ворота зелёные; релиз 0.31.0
