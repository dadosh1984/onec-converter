# Полный цикл: clone-db → load → verify → audit → verify_audit (Фаза 46)

Сквозной сценарий миграции на стенд с полной проверяемостью. Все команды —
`onec-converter`; тесты в `E:\test`, ворота — `bash scripts/gates.sh`.

## 1. Стенд: копия источника (оригинал не трогается)
```bash
onec-converter clone-db ./source_ib ./stand --with-rules rules.json
# копирует 1Cv8.1CD целиком + rules/ рядом; прогресс-логи (Фаза 46)
```

## 2. Извлечение из копии (чтобы не блокировать боевую ИБ)
```bash
onec-converter extract --source-dir ./stand --objects "Справочник.*,Документ.*" \
    --out extract.json --audit-file audit.jsonl
```

## 3. Трансформация по правилам
```bash
onec-converter transform --rules rules.json --input extract.json --out batch.json
```

## 4. Загрузка в приёмник (HTTP-расширение или прямая запись)
```bash
onec-converter load --http http://<server>/loader/hs \
    --secret "CHANGE-ME-AND-KEEP-SECRET" \
    --input batch.json --audit-file audit.jsonl
# или прямая запись в 8.x: load --direct ./tgt_ib --input batch.json
```

## 5. Проверка целостности приёмника
```bash
# прочитать объекты из приёмника и сверить с источником (Фаза 48)
onec-converter extract --source-dir ./tgt_ib --out tgt_read.json \
    --objects "Справочник.Контрагенты"
onec-converter verify --input extract.json --target tgt_read.json \
    --objects "Справочник.Контрагенты"
# rc=0 — полное совпадение (ключ+атрибуты); --json — отчёт для CI
# {ok, total_source, total_target, matched, missing, mismatched}
```

## 6. Аудит «кто/что/когда»
```bash
onec-converter audit --file audit.jsonl --level ERROR --op load
onec-converter pii-report --audit-file audit.jsonl --rules-file rules.json
# сводка ПДн (152-ФЗ / 152 УЗ): какие поля были анонимизированы
```

## 7. Проверка tamper-evident цепочки (комплаенс, Фаза 42/46)
```bash
onec-converter audit-verify --audit-file audit.jsonl --cross-files
# SHA-256 цепочка: prev_hash первой записи пуст; ротация — маркер
# {"marker":"rotated","prev_hash":…}; границы архивов .1/.2/… сверяются
```
Запускайте шаг 7 в CI/по расписанию — любое изменение журнала (правка,
удаление записи) ломает хеши и детектируется.

## Масштабирование
- Большие объёмы: `extract --limit N` порциями, пакеты до 500 объектов на
  запрос (расширение onec_loader).
- Идемпотентность: повторный `load` без `replace` не перезаписывает
  существующее (поиск по ключу с нормализацией `СокрЛП`).
