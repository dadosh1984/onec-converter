# Формат файловой ИБ 1С 7.7 (текстовый вариант) — результаты спайка

Проверено на реальной базе `БАЗА 31.07.202` (платформа 7.70).

## Состав каталога базы

| Файл | Содержимое | Формат |
|---|---|---|
| `1Cv7.MD` | Метаданные конфигурации (дерево объектов, реквизиты, типы, модули, формы) | OLE2 compound document (`d0 cf 11 e0 a1 b1 1a e1`), вложенные storage `Container.Contents` |
| `1Cv77.dat` | **Все данные ИБ** (справочники, документы, регистры, константы) | Текст, JSON-подобный, CP866, CRLF |
| `users.usr` | Список пользователей | OLE2 (для переноса не нужен) |

## `1Cv77.dat` — структура секций

```
{"7.70","",                              ← заголовок (версия платформы)
{"System table", {...}},
{"Unique IDs", {id_таблицы,"счётчик|", ...}},   ← число записей по каждой таблице
{"Constants", {id, {"0|",дата,"0|",0,0,0,значение}, ...}},
{"References", {id_записи, {...}, ...}},       ← ВСЕ справочники (по таблицам)
{... документы, журналы, регистры ...},
{"Template Operations"},
{"Correct Entries"}}
```

- Секции верхнего уровня — имена в кавычках: `System table`, `Unique IDs`, `Constants`, `References`, далее данные документов/регистров, в конце `Template Operations`, `Correct Entries`.
- Внутри бухгалтерских операций встречаются вложенные структуры `{"Actions", ...}` / `{"Accounting", ...}`.
- Записи — кортежи значений через запятую: `{...}`.

### Кодировки и типы значений
- Текст: **CP866** (DOS) → конвертация в UTF-8.
- Ссылки: строки `"NNN|"` — внутренний числовой ID записи + суффикс `|`. Пустая ссылка: `"0|"`; нулевой GUID: `00000000-0000-0000-0000-000000000000`.
- Даты: `YYYYMMDD` (без кавычек), напр. `20241204`.
- Числа: десятичная точка, точность `0.00` / `0.000`.
- Строки: в кавычках; код справочника — с фиксированной шириной и ведущими пробелами (напр. `"   94"`).
- Идентификаторы записей — сквозные числа (193|, 277|, 3405|…), у каждой таблицы своя нумерация (см. `Unique IDs`).

## `1Cv7.MD` — OLE2-контейнер метаданных

Top-level storage (19): `AccountChart`, `AccountChartList`, `CalcJournal`, `CalcVar`,
`Container.Contents`, `Document`, `GlobalData`, `Journal`, `Metadata`, `Operation`,
`OperationList`, `Picture`, `ProvList`, `Report`, `SubFolder`, `SubList`, `Subconto`,
`TypedText`, `UserDef`.

- Каждый объект конфигурации — отдельный storage: `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354` и т.д.
- Внутри объекта: потоки `Container.Contents` (сериализованный объект), `WorkBook`
  (формы), `Dialog Stream`, `MD Programm text` (модули), `Page.N`, `Container.Profile`, `Commands`.
- Дерево объектов (справочники, документы, реквизиты, типы, перечисления) —
  предположительно в storage `Metadata` / `GlobalData`.

### Открытые вопросы спайка
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов).
- [ ] Где именно лежит описание справочников и их реквизитов (имена, типы, точность чисел).
- [ ] Точный порядок секций `1Cv77.dat` для документов, журналов, регистров (остатки/обороты).
- [ ] Маппинг ID-таблиц (`Unique IDs` → имена объектов через метаданные MD).

## Зависимости
- `olefile` — чтение OLE2 `1Cv7.MD` (уже установлена).
- Парсер `1Cv77.dat` — собственный (формат простой, без внешних библиотек).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).

### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}`.

Терминалы (для парсера v77_reader):
- строка: `"…"`, кавычки внутри удваиваются `""`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: `YYYYMMDD` без кавычек (20241204);
- ссылка: `"NNN|"` (внутренний числовой ID), пустая — `"0|"`;
- Unique IDs: `{id_таблицы, "счётчик|"}` (напр. `{81,"312|"}`);
- запись справочника: `{"193|","0|","  221","","0|",0,0,"00959","","",""}`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные `{"Actions"}`/`{"Accounting"}` внутри операций.

### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage `Document/Document_Number1015`,
  `CalcVar/CalcVar_Number2451`, `Subconto/Subconto_Number354`; внутри — потоки
  `Container.Contents` (сериализованный объект), `WorkBook`, `Dialog Stream`,
  `MD Programm text`, `Page.N`, `Container.Profile`, `Commands`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока `Container.Contents` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage `Metadata`/`GlobalData`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).
