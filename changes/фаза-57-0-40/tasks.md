# Задачи — Фаза 57 (0.40.0): безопасность

- [x] E3: _resolve_secret (флаг > env ONEC_SECRET > TTY), применён в mint-token и load
- [x] E1: проверка mask_dsn в sql_source (уже маскирует, нет-оп)
- [x] E4: snapshot-политика зафиксирована через --no-snapshot (тест snapshot=True/False)
  - авто-удаление snapshot на успехе отклонено (не ломает контракт отката)
- [x] тесты Фазы 57 (4), ворота green (pytest 538 / ruff / mypy)
- [x] версия 0.40.0, openapi, CHANGELOG
