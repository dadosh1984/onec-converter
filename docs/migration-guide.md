# Перенос данных между ИБ 1С через onec-converter — полный алгоритм

Рабочая инструкция: от копии исходной базы до сверки полноты переноса в приёмнике.
Все команды выполняются из корня проекта (`E:/SYSTEM/Desktop/AI_Projects/onec_converter`).

> **Правило безопасности**: работаем ТОЛЬКО с копиями баз. Оригинал никогда
> не подаётся на вход командам записи (`bridge-import`, `load_direct`, `migrate --direct`).

---

## 0. Подготовка окружения

| Команда | Ожидаемый результат |
|---|---|
| `py -3.14 -m onec_converter.cli doctor` | Все проверки OK; версия 0.46.0 |
| `git check-ignore XML_8.1 XML_8.3` | Печатает оба пути — папки выгрузок НЕ попадут в git |
| Создать КОПИИ баз: `1C_8.1_копия/1Cv8.1CD`, `1C_8.3_копия/1Cv8.1CD` | Оригиналы не будут изменяться |

Разведка данных (необязательно, но полезно до старта):

| Команда | Ожидаемый результат |
|---|---|
| `onec-converter inspect --source-dir <копия источника>` | Метаданные: таблицы, поля, типы |
| `onec-converter stats --source-dir <копия источника>` | Сводка: таблицы / строки / объём / locale |
| `onec-converter fetch-config --source XML_8.1` | `{"ok": true, "total": 787}` — метаданные конфигурации без чтения .1CD |
| `onec-converter guid-diff --source-dir <копия 8.1> --target-dir <копия 8.3>` | Сверка двух баз по GUID (полнота объектов/таблиц) |
| `onec-converter ai-explain --source-dir <копия 8.1> --target-dir <копия 8.3>` | Причины расхождений структур |

---

## 1. Правила переноса (map)

Правила TOON — сердце переноса: какой объект источника в какой объект приёмника,
какие поля как маппятся, как разрешаются ссылки.

```bash
# Сгенерировать шаблон правил из метаданных источника (объект -> та же таблица приёмника)
onec-converter map --init \
  --meta-source <копия источника> \
  --meta-target <копия приёмника> \
  --out rules.json
```

| Ожидаемый результат |
|---|
| `rules.json` — для каждого объекта источника правило «в ту же таблицу» приёмника |

Затем **вручную правим `rules.json`**: маппинг полей (имена/типы), ключевые поля,
ссылки, преобразования. Альтернатива — автогенерация маппинга по схемам:

```bash
onec-converter ai-map --source-dir <копия 8.1> --target-dir <копия 8.3>
```

| Ожидаемый результат |
|---|
| Авто-маппинг схем → правила TOON (поля сопоставлены по именам/типам) |

---

## 2. Выгрузка данных (extract)

```bash
onec-converter extract \
  --source-dir <копия источника> \
  --source-encoding cp866 \          # только для 7.7; 8.x — не указывать
  --out intermediate.json
```

| Ожидаемый результат |
|---|
| `intermediate.json` — объекты в промежуточном формате (type/key/attributes/references), UTF-8 |

Проверка выборки по одному объекту до полного прогона:
`onec-converter query --source-dir <копия> --sql "SELECT * FROM Справочник.Банки LIMIT 5"`.

---

## 3. Преобразование (transform)

```bash
onec-converter transform \
  --rules-file rules.json \
  --input intermediate.json \
  --out target_objects.json \
  --audit-file audit.jsonl
```

| Ожидаемый результат |
|---|
| `target_objects.json` — target-объекты приёмника (правила применены) |
| `audit.jsonl` — журнал аудита переноса (JSONL) |

Предпросмотр одного объекта перед полным прогоном: `--preview <имя объекта>`.

---

## 4. Загрузка в приёмник

Три способа — по возрастанию «прямоты»:

### 4а. Сквозной перенос одной командой (рекомендуется для полного цикла)

```bash
onec-converter migrate \
  --source-dir <копия источника> \
  --rules rules.json \
  --out migrate_result.json
```

| Ожидаемый результат |
|---|
| Выполняет extract→transform→load последовательно; `migrate_result.json` со статистикой |

### 4б. Прямая запись в копию 1CD приёмника (без HTTP)

```bash
onec-converter migrate --source-dir <копия> --rules rules.json --direct <копия приёмника 1CD>
# или отдельно
onec-converter load --input target_objects.json --direct <копия приёмника 1CD>
```

| Ожидаемый результат |
|---|
| Объекты записаны в КОПИЮ `1Cv8.1CD` приёмника; `LoadResult {created, updated, errors}` |

> Прямая запись работает только с полноценной копией 1CD (нужны PARAMS).

### 4в. HTTP-загрузка (приёмник с расширением /load)

```bash
onec-converter load --input target_objects.json --http http://<приёмник>/load
```

| Ожидаемый результат |
|---|
| Батчи ≤500 объектов с retry; `LoadResult` |

---

## 5. Сверка полноты (verify)

### 5а. Сверка источник ↔ приёмник

```bash
onec-converter verify --input intermediate.json --target target_objects.json --json
```

| Ожидаемый результат |
|---|
| Отчёт в JSON для CI: количество/ссылки/дубликаты — полнота переноса |

### 5б. Обратный контроль через xlsx-мост (bridge-verify)

Проверяет, что данные КОПИИ приёмника совпадают с мостом (обратная выгрузка из
приёмника и сверка построчно):

```bash
# 1. Выгрузить объект из КОПИИ источника в xlsx-мост (эталон)
onec-converter bridge-export --source-dir <копия источника> --type Справочник.Банки --out bridge.xlsx

# 2. Записать мост в КОПИЮ приёмника
onec-converter bridge-import --input bridge.xlsx --target-dir <копия приёмника 1CD>

# 3. Обратная сверка: копия приёмника <-> мост
onec-converter bridge-verify --input bridge.xlsx --target-dir <копия приёмника 1CD> \
  --key Код,Наименование --ignore-cols _VERSION,_MARKED
```

| Ожидаемый результат |
|---|
| Отчёт `{matched, mismatched, missing, extra, diffs, ok}` — полное совпадение при ok=true |
| Ключи: `--key` — составной ключ сверки, `--ignore-cols` — служебные колонки |

### 5в. Сверка GUID двух баз

```bash
onec-converter guid-diff --source-dir <копия 8.1> --target-dir <копия 8.3>
```

| Ожидаемый результат |
|---|
| Diff по GUID: какие объекты/таблицы перенесены, каких нет |

---

## 6. Контроль качества переноса

```bash
# Целостность журнала аудита (tamper-evident хеш-цепочка)
onec-converter audit-verify --input audit.jsonl

# Контроль целостности КОПИИ приёмника после прямой записи
onec-converter doctor
```

| Ожидаемый результат |
|---|
| `audit-verify` — rc=0 при целой цепочке (нет подмен записей) |

---

## Схема потока

```
копия источника (.dat / .1CD)
   │ extract
   ▼
intermediate.json ──────────────► map --init + ai-map → rules.json
   │ transform (rules.json)
   ▼
target_objects.json ──► migrate / load --direct|--http ──► КОПИЯ приёмника .1CD
   │                                                          │
   ▼                                                          ▼ bridge-export/import
verify (полнота)                                        bridge.xlsx
   │                                                          │ bridge-verify
   └── guid-diff / audit-verify ◄────────────────────────────┘
```

## Чек-лист перед стартом

- [ ] `doctor` OK
- [ ] Копии обеих баз созданы (оригиналы не трогаем)
- [ ] XML_8.1/XML_8.3 в `.gitignore` (проверено `git check-ignore`)
- [ ] `rules.json` проверен: ключевые поля, маппинг полей, ссылки
- [ ] Пробный прогон на одном объекте (`query` + `transform --preview`)
- [ ] После записи — `bridge-verify` и `guid-diff`
