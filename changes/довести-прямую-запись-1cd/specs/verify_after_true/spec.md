# Spec: verify_after_true

## Purpose
Довести прямую запись в 1CD до производственной надёжности: верификация
после записи, атомарный replace (без полу-записи), ясные ошибки лимитов,
чистка tmp.

## Requirements
- [REQ-1] `load_direct(..., verify_after=True)` — после записи читает копию
  парсером и сверяет roundtrip без потерь; результат в отчёте `verify`.
- [REQ-2] Атомарность: запись во временный `work.1CD`, по завершении
  `os.replace(work → 1Cv8.1CD)`; сбой не оставляет полузаписанный финальный
  файл.
- [REQ-3] Ошибки лимитов: `max_objects` (превышение → LoadError); ENOSPC →
  LoadError «недостаточно места на диске», work чистится; LockError (уже есть).
- [REQ-4] Чистка tmp: временные work-файлы удаляются (в normal и при ошибке);
  финальный `1Cv8.1CD` в workdir не трогается.
- [REQ-5] Документация: разделы «Проверка копии перед использованием» в
  `docs/zero-setup.md`, `docs/playbook.md`, `README.md`.
- [REQ-6] Ворота: pytest, ruff, mypy strict, vitest; тесты в `E:\test`
  (basetemp), не забивая системный tmp.
