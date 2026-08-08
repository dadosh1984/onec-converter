# Forge Report — довести-прямую-запись-1cd

- **Status:** complete
- **Done:** 10 · **Skipped (cache):** 1 · **Pending:** 0
- **Generated:** 2026-08-08T16:15:44.750Z

| Task | Status |
|------|--------|
| [spike] docs/zero-setup.md + docs/playbook.md: раздел «Проверка копии | done |
| [fact] `test_verify_detects_corruption` — после порчи записи verify.full | done |
| [fact] `test_cleanup_workfile_on_error` — при ошибке work.1CD удалён, | done |
| [fact] `test_enospc_clear_error` — нехватка диска → LoadError с понятным | done |
| [fact] атомарный replace: копия исходника → `wd/work.1CD`, append в него, | done |
| [fact] `verify_after=true`: после записи прочитать объекты из финальной | done |
| [fact] reader строки→объект (декодирование по полям таблицы) в | done |
| [fact] ошибки лимитов: ENOSPC → LoadError «недостаточно места»; | done |
| [fact] чистка tmp: удалять work.1CD/мусор, не трогая финальный 1Cv8.1CD | done |
| [fact] tests/test_load_8x_verify_e2e.py: load_direct реального объекта | skipped |
| [assumption] README/docs — как проверить копию перед использованием | done |


