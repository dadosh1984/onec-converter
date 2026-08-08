# Пайплайн переноса данных (end-to-end, Фаза 7)

Полный путь переноса между ИБ 1С: **7.7 → 8.3** (и, по тем же шагам,
8.x → 8.3). Каждый коннектор покрыт unit-тестами отдельно; эта
документация фиксирует поток данных целиком и стыковку шагов.

## Поток данных

```
Base77 (1Cv77.dat, cp866/cp1251)          ← источник 7.7 (read-only)
   │  step_extract / read_table
   ▼
intermediate JSON  (save_json_batch, UTF-8)
   │  step_map → transform (TOON-правила, transform_object)
   ▼
target-объекты (type/key/attributes/references)
   │  validate_batch (количество / ссылки / дубликаты)
   ▼
HttpClient83 → POST /load (батчи ≤500, retry)   ← приёмник 8.3 (расширение)
   ▼
LoadResult {created, updated, errors} → verify (сверка)
```

## Шаги пайплайна (MCP)

| Шаг | Команда | Вход → Выход |
|-----|---------|--------------|
| 1 | `step_init(project, src, tgt, dir, encoding)` | каталог 7.7 → привязка 1→1 (project.json) |
| 2 | `step_inspect_source()` | .dat → метаданные (секции, references, constants) + кеш |
| 3 | `step_extract(out_file)` | references → intermediate JSON (UTF-8) |
| 4 | `step_map(meta_src, meta_tgt, rules)` | правила TOON → валидация + промпт LLM |
| 5 | `transform` | intermediate + правила → target-объекты |
| 6 | `step_prevalidate()` | target-объекты → отчёт {ошибки, warnings, counts} |
| 7 | `step_load(http_load)` | target-объекты → HTTP /load → LoadResult |
| 8 | `verify` | сверка источник↔приёмник (полнота переноса) |

Всё одним вызовом: тул `migrate(project_dir, source_ib_id, target_ib_id,
source_dir, target_url, rules, out_file, source_encoding)` — выполняет шаги
1–7 последовательно; каждый шаг логируется в терминал (▶/✔/✘) и попадает
в `steps` ответа с временем выполнения.

## Формат батчей (HTTP /load)

```json
{"source_ib": "8.1", "target_ib": "8.3", "replace": false,
 "objects": [{"type": "Справочник.Банки", "key": ["00001", "…"],
              "attributes": {"Код": "00001", "Наименование": "…"},
              "references": {}}]}
```

Ответ: `{"created": N, "updated": N, "errors": []}`. Кодировка — UTF-8
(тексты 7.7 перекодируются из cp866/cp1251 на стыке чтения — A4 middleware).

## Стыковка коннекторов

- **7.7 → intermediate**: `Base77.data.references()` — {id таблицы: записи};
  каждая запись → объект intermediate (`type=Справочник.<id>`, key=[код, имя],
  attributes {_code, _descr}).
- **intermediate → target**: `transform_object(obj, rule, resolver)` —
  переносит attributes по правилу `{source: target}`; ссылки — через
  RefResolver (для 7.7 references пустые).
- **target → 8.3**: `HttpClient83.load(objects, src, tgt)` — пакеты по 500,
  retry с экспоненциальной задержкой; приёмник отклоняет чужую пару (409)
  — правило 1→1.

## Ограничения

- Реальные базы читаются только **read-only**; запись — только через
  HTTP-сервис приёмника (расширение 8.3) или HTTP-mock в тестах.
- Сквозной тест (tests/test_pipeline_e2e.py) работает на синтетике
  (gen_dat) с httpx.MockTransport — реальные базы не затрагиваются.
