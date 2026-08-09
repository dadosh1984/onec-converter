# Skill: context_compressor (Фаза 40)

Сжимает метаданные базы (тысячи объектов) до краткого саммари для
контекстного окна LLM — вместо выгрузки всех объектов целиком.

## Использование (Python/скрипт)

```python
from onec_converter.source_8x_file import read_metadata
from onec_converter.ai_skills import compress_metadata

meta = read_metadata("src/1Cv8.1CD")
summary = compress_metadata(meta, top_tables=15)
print(json.dumps(summary, ensure_ascii=False, indent=2))
# {'kinds': {'Справочник': 120, 'Документ': 45, 'РегистрСведений': 30},
#  'objects': 195, 'tables': 195, 'top': [...по числу реквизитов],
#  'total_attrs': 4120}
```

## Как использовать агентам
1. Сначала сделать `summary` (2-3 КБ вместо мегабайт).
2. Для интересующего типа запросить детали через `search_schema`/`dump_metadata`.
3. Правила строить через `auto_map_schemas` — их меньше править, чем генерить с нуля.

## Промпт-подсказка
> Имеется метаданные базы 1С. Суммаризируй состав: число справочников,
> документов, регистров; назови 5 самых крупных объектов. Не перечисляй все
> 5000 таблиц.
