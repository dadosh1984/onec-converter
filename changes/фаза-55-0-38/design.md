# Дизайн — Фаза 55 (0.38.0): интерактивность и UX

По аудиту раунда 6 (docs/audit-round-6d.md), раздел F/G.

## Сделано
- F1/F2: `--pretty` — человек-читаемые ASCII-таблицы в inspect/query/\n  stats/guid-diff. Авто-включение по TTY; `--no-pretty`/pipe оставляет JSON\n  (машиночитаемость не нарушена).
- терминал: `terminal.render_table` (без зависимостей), `terminal.is_tty`.
- G1/G3/F4: `--help` сгруппирован по категориям (Разведка/Перенос/Проверка/\n  Отчёты и аудит/Служебные): `_CategoryHelpFormatter` + `COMMAND_CATEGORIES`;\n  корневые `--pretty`/`--no-pretty`.
- F3: `_done_note` — заметки о завершении шагов (stderr, только TTY) в\n  extract/transform/load.
- H-fix: cp1251-консоль — CLI больше не падает UnicodeEncodeError в `--help`\n  (UTF-8 reconfigure в main) — раньше `↔` роняла вывод.

## Перенесено в Фазу 56 (честно)
- G2 `wizard` и C4 `migrate` (guided/full-pipeline CLI) реализуются вместе\n  в Фазе 56 как единая возможность; здесь — только UX-фундамент (pretty).

## Сознательно НЕ делал (баланс)
- Не трогал JSON-вывод по умолчанию (не-TTY) — обратная совместимость\n  со скриптами сохранена.

## Верификация
- ruff/mypy clean; pytest 528 green (+9 Фаза 55); vitest 355; openapi 0.38.0.
