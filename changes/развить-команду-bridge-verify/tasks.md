# Задачи — развить-команду-bridge-verify

Приоритет: надёжность сравнения (идеи 1–4 пропозала). Ворота: pytest, mypy strict, ruff, vitest зелёные; без новых зависимостей; только копии баз.

- [x] [fact] `normalize_value(v)` в bridge_verify: числа (int/float — 1 == 1.0), даты (datetime/date -> iso-строка), bool, строки (strip, убрать \r, 'None'/'NoneType' -> None, пусто -> None), возвращает нормализованное значение; юнит-тест на ложные mismatched (1 vs 1.0, ' 1 ' vs 1, '' vs None)
- [x] [fact] `compare_code` использует normalize_value для всех колонок обеих строк перед сравнением; юнит-тест: мост с 1 vs 1.0 в числовой колонке не даёт mismatched
- [x] [fact] `diff на уровне полей`: для 'different' в diffs добавлять список расхождений по колонкам [{'col': attr, 'in': ..., 'out': ...}] вместо тупого сравнения всей строки; юнит-тест: одна изменённая колонка -> diff только по ней
- [x] [fact] составной ключ: `_key_index` поддерживает список ключевых колонок (tuple ключ); `compare_code(key_col='a,b')` парсит список; юнит-тест: ключ по двум колонкам, дубликат одной части не ломает сравнение
- [x] [fact] `--ignore-cols` в `compare_code`/`verify_roundtrip`/CLI: колонки исключаются из сравнения (значения не участвуют в diff); юнит-тест: _Version/_Marked игнорируются, изменения в них не дают mismatched
- [x] [fact] CLI bridge-verify: флаги --key (список через запятую) и --ignore-cols (список через запятую), передаются в verify_roundtrip; контракт-тест CLI (registry) на новые флаги
- [x] [assumption] README/документация: раздел bridge-verify с описанием normalize, составного ключа, --ignore-cols
