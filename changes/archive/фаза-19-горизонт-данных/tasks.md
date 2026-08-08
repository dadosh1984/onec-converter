# Tasks — Фаза 19: горизонт данных

Ворота: mypy strict, ruff, pytest, vitest. Авторский код.

## Регистры
- [x] [fact] подтверждено: `read_metadata` распознаёт регистры (kinds
      РегистрСведений/Накопления/ПланСчетов); запись через load_direct работает
- [x] [fact] e2e-тест `tests/test_load_8x_registers.py`: запись строки регистра
      сведений в копию (измерение + ресурс) — парсер читает
- [x] [spike] docs/format-8x.md: раздел «Регистры (Фаза 19)» — поля _INFORG/
      _ACCUMRG (измерения, ресурсы, _SIMPLEKEY), запись

## Module.bsl — replace и Документы
- [x] [fact] обработка `replace` (поиск по коду `Код`/номеру → обновить, Обновлено++)
- [x] [fact] поддержка `Документ.*` (создание документа, search по номеру)
- [x] [fact] метаданные: включить Документы в GET /metadata

## Пустые таблицы и 1Cv8.dt — осознанные ограничения (spike-документация)
- [x] [spike] docs/format-8x.md: пустые таблицы (data_page=0) — ограничение,
      обоснование; 1Cv8.dt — spike-статус (не распознан)

## Верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] docs/development-plan.md: Фаза 19 отмечена выполненной
