# Skill: autonomous_migration (Фаза 40)

Сквозной сценарий миграции по командам CLI — первый запуск без участия
человека. Все шаги используют read-only диагностику и прямую запись со
snapshot/index-repair. Подходит для повторного запуска (идиempotent).

## Сценарий (bash)

```bash
# 0. Контекст
SRC="./src"          # источниковая ИБ 8.x (1Cv8.1CD)
TGT="./tgt"          # приёмник 8.x (структура готова заранее)
RULES="rules.json"

# 1. Диагностика (read-only)
onec-converter base_health --source-dir "$SRC"
onec-converter inspect --source-dir "$SRC" --out meta_source.json

# 2. Авто-правила (детерминированная эвристика)
#    (MCP-тул auto_map_schemas, Фаза 40; в CLI — через скрипт-json)
python - <<'PY'
import json
from onec_converter.source_8x_file import read_metadata
from onec_converter.ai_skills import auto_map_schemas
res = auto_map_schemas(read_metadata("$SRC/1Cv8.1CD"),
                       read_metadata("$TGT/1Cv8.1CD"))
json.dump({'version': 1, 'objects': res['rules'], 'enums': {}},
          open("$RULES", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"matched={res['matched']} unmatched={res['unmatched']}")
PY

# 3. Перенос
onec-converter extract --source-dir "$SRC" --out extract.json
onec-converter transform --input extract.json --rules-file "$RULES" --out transformed.json
onec-converter clone-db --source-dir "$TGT" --target-dir ./work_target   # стенд/копия
onec-converter load --direct ./work_target --input transformed.json \
    --workdir ./work --index-repair --audit-file audit.jsonl

# 4. Проверка
onec-converter verify ./work_target   # или query выборочно
onec-converter pii-report --audit-file audit.jsonl --rules-file "$RULES"
onec-converter metrics                      # строк/сек, ошибки
```

## Повторяемость
- `clone-db` + `snapshot.1CD` (в `workdir`) дают откат.
- `load --index-repair` генерирует скрипт восстановления индексов.
- Аудит `audit.jsonl` (tamper-evident) — доказательство для комплаенса.
