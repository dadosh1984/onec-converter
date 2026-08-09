# Дизайн — изучить-типовую-обработку-1с

## Обзор
Детерминированный план, выведенный из предложения. Реализация ведётся
задачу за задачей через цикл RED-GREEN-REFACTOR; каждая задача из чеклиста
в tasks.md становится одним тест-управляемым юнитом в `src/tasks/*`.

## Модули

- `src/tasks/*` — тест-управляемые юниты реализации (по одному на задачу)
- `tests/*` — тест-файлы RED-GREEN-REFACTOR (пишутся первыми, RED)
- `changes/изучить-типовую-обработку-1с/snippets/*` — подсказки реализации по задачам

## Допущения
- Scaffold project structure for изучить-типовую-обработку-1с
- Implement the core parsing/transformation pipeline
- Add format conversion: validation, edge cases, error reporting
- Add parsing: tokenizer/grammar, syntax errors
- Cover the core capability with tests
- Document usage in README

## Верификация
Задача считается сданной, только когда проходят все гейты:

- [ ] lint (pnpm lint)
- [ ] проверка типов (tsc --noEmit)
- [ ] юнит-тесты (pnpm test)
