# Рецепт: сквозной перенос одной командой (migrate)

Фаза 56 (0.39.0). `migrate` — сквозной перенос одной командой
(extract → transform → load), заменяет цепочку
`inspect/extract/map/transform/load` для типового случая.

## Быстрый старт

```
# данные ИБ источника → один JSON-файл (без правил = копия без трансформации)
onec-converter migrate --source-dir "./src" --out migrated.json --workers 2
```

## С правилами маппинга (TOON)

```
onec-converter migrate \
    --source-dir "./src" \
    --rules rules.json \
    --out migrated.json \
    --source-encoding cp866
```

Объекты без правила в rules.json пропускаются (безопасно); сообщение —
«без правила: N» в stderr.

## Прямая запись в копию приёмника (zero-setup)

```
onec-converter migrate \
    --source-dir "./src" \
    --rules rules.json \
    --direct "./target" \
    --workdir "./work"
```

Прямая запись работает только с копией `1Cv8.1CD` приёмника; оригиналы
не изменяются. `--no-snapshot` отключает откат-копию (экономия места),
`--workers N` — число потоков чтения для 8.x.

## Интерактивный мастер (wizard)

```
onec-converter wizard
```

Задаёт вопросы (источник, кодировка, правила, приёмник, выходной файл)
и собирает/запускает `migrate`. `--no-run` печатает команду без
выполнения (безопасно проверить перед запуском).

## Что делает под капотом

1. `_detect_version` → 7.7 (cp866/cp1251) или 8.x (1Cv8.1CD).
2. `extract` — объекты в промежуточный формат (совместимо с
   `verify`/`query`).
3. `transform` (если заданы rules) — применяет TOON-правила.
4. `load` — файл (JSON) или `--direct` в копию 1CD.

Полная карта команд — `docs/commands-map.md`; карта подходов — `docs/plan.md`.
