# Tasks — производственная надёжность записи в 1CD (Фаза 16)

Ворота: mypy strict, ruff, pytest, vitest. Запись только на копиях.

## Spike (документация)
- [x] [spike] docs/zero-setup.md + docs/playbook.md: раздел «Проверка копии
      перед использованием» — verify после записи, атомарный replace,
      лимиты/ошибки, чистка tmp; ограничение «индексы не пересобираются»

## RED — тесты на нереализованном
- [x] [fact] tests/test_load_8x_verify.py: `test_verify_after_load_full` —
      load_direct с verify_after=True возвращает verify.full==True — FAIL
- [x] [fact] `test_verify_detects_corruption` — после порчи записи verify.full
      False (mismatched) — FAIL
- [x] [fact] tests/test_load_8x_atomic.py: `test_atomic_replace_no_partial` —
      при ENOSPC нет «полузаписанного» финального 1Cv8.1CD — FAIL
- [x] [fact] `test_cleanup_workfile_on_error` — при ошибке work.1CD удалён,
      wd чистый от мусора — FAIL
- [x] [fact] `test_enospc_clear_error` — нехватка диска → LoadError с понятным
      текстом — FAIL

## GREEN — реализация в load_8x.py (+ load_8x_refs при необходимости)
- [x] [fact] атомарный replace: копия исходника → `wd/work.1CD`, append в него,
      по завершении `os.replace(work.1CD → 1Cv8.1CD)`; finally-чистка work
- [x] [fact] `verify_after=true`: после записи прочитать объекты из финальной
      копии, свернуть в {type,key,attributes}, `verify(objects, read)` →
      отчёт `verify`
- [x] [fact] reader строки→объект (декодирование по полям таблицы) в
      load_8x_refs (или load_8x)
- [x] [fact] ошибки лимитов: ENOSPC → LoadError «недостаточно места»;
      опция `max_objects` (превышение → LoadError)
- [x] [fact] чистка tmp: удалять work.1CD/мусор, не трогая финальный 1Cv8.1CD

## GREEN — e2e на копии 8.1
- [x] [fact] tests/test_load_8x_verify_e2e.py: load_direct реального объекта
      на копии 8.1 → verify.full True; порча строки → False

## Постусловия / верификация
- [x] [assumption] pytest (все), ruff, mypy strict, vitest — зелёные
- [x] [assumption] README/docs — как проверить копию перед использованием
