# Диалог LLM-агента (Claude/Cursor) с MCP-тулами (Фаза 46)

Пример использования `auto_map_schemas` и `explain_diff` из MCP-сервера
(список тулов — `onec-converter mcp`). Агент оперирует проверяемыми
структурами, а не галлюцинирует о полях.

## Сценарий: подготовить перенос «Бекас -> Бухгалтерия 3»

```
Пользователь:  Разбери расхождения схем и подготовь правила для переноса.
Агент:         [onec-converter compare_structures source=./bekas target=./buh3]

               only_source: Документ.ПриходныйОрдер, Справочник.Склады
               only_target: Документ.ПриходнаяНакладная
               type_mismatch: Документ.АвансовыйОтчет.Сумма N -> NC

Агент:         [onec-converter explain_diff source=./bekas target=./buh3]
               > Только в источнике: объект/поле Документ.ПриходныйОрдер
                 отсутствует в приёмнике.
               > Изменён тип: Документ.АвансовыйОтчет.Сумма N -> NC.

Пользователь:  Автоматически сопоставь похожие объекты.
Агент:         [onec-converter auto_map_schemas source=./bekas target=./buh3]
               matched: 214, unmatched: 3
               rules[0]: Справочник.Контрагенты -> Справочник.Контрагенты
                         (confidence: exact, атрибуты: Наименование, ИНН, …)
               rules[7]: Документ.Продажа -> Документ.РеализацияТоваров
                         (confidence: synonym — подтвердить оператору)

Агент:         Вывод: 214 объектов маппятся точно, 3 «синонимичных» требуют
               подтверждения. Сумма меняет тип N->NC — перед переносом
               сконвертируй значения через transform. Правила сохранил в
               rules.json (формат TOON) — передаю в load.
```

## Что это даёт

- `explain_diff` — причины расхождений человекочитаемо (не сырой diff).
- `auto_map_schemas` — готовые правила с уровнем уверенности; `synonym`
  помечается как требующий подтверждения (Фаза 45).
- `compress_metadata(meta, out_path=…)` — краткое саммари структуры для
  контекста агента вместо тысяч объектов (Фаза 40/45).
- Агент не угадывает имена полей: сопоставление детерминировано и
  проверяемо.

## Сценарий 2: сжатие метаданных + комплаенс (Фаза 51)

```
Пользователь:  Оцени объём базы и сколько инвентарей затронет перенос.
Агент:         [onec-converter compress_metadata source=./bekas top_tables=10]
               kinds: {Справочник: 42, Документ: 17, РегистрСведений: 8},
               objects: 67, tables: 67, top: [Справочник.Контрагенты …]
               → сжато: вместо тысяч объектов агенту отдано 10 строк.

Пользователь:  Перенос уже делался вчера — проверь целостность журнала.
Агент:         [onec-converter audit_verify audit_file=./logs/audit.jsonl cross_files=true]
               ok: true, errors: [] — хеш-цепочка и границы ротации целы.

Пользователь:  Сколько кеш-артефактов накопилось?
Агент:         [onec-converter cache_stats root_dir=.onec_cache]
               files: 231, bytes: 482134, oldest: 3 дня назад.
```

## Роль inspect (read-only агент, Фаза 51)

При `ONEC_MCP_ROLE=inspect` write-тулы (`migrate`, `load_direct`) и write-шаги
плейбука (`init/extract/map/transform/load/preview`) скрыты из списка тулов и
блокируются — агент может только читать/сверять/планировать, но не менять базы.
Список для роли (read-only): base_health, table_sizes, compare_structures,
auto_map_schemas, explain_diff, search_schema, query_sql, guid_diff,
config_versions, dump_metadata, compress_metadata, audit_verify, cache_stats.
