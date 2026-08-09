# Spec: core

## Purpose
Раскрыть «невидимое нулевое покрытие» (U6): 9 модулей вне coverage-замера
и без dedicated-тестов. Довести покрытие до 70%+ честными юнит-тестами;
защитить от деградации производительности и от реального покрытия-в-0.
Версия 0.33.0.

## Acceptance criteria
- [x] coverage_modules включает 9 новых модулей (U43); порог 70;
      итоговое покрытие >= 70% (факт 90%)
- [x] dedicated-тесты 9 модулей в tests/test_phase50_coverage.py (U44):
      kd3_export, sonar_report, gdpr_152_report, source_techlog (уже был),
      notify, terminal, strict, type_priority, s3_client (уже был)
- [x] strict: ref-поле любого значения валидируется (fix молчаливого
      пропуска не-bytes/str ссылок)
- [x] property round-trip fake-1CD (U47): seeded random базы
      build_fake_1cd -> Database1CD -> те же таблицы/поля/число строк
- [x] hypothesis fuzz (U50): Cache round-trip и strict приём чисел;
      hypothesis>=6 в dev
- [x] gates.sh benchmark с порогами (U49): BENCH_META_MS_MAX,
      BENCH_READ_MS_MAX; падает при деградации, ловит её
- [x] Windows CI-джоба (U48): unit + coverage + conformance
- [x] gates.sh: CRLF в именах модулей убран (\\r не ломает датчик),
      PYTHONPATH=src для benchmark и pytest-coverage
- [x] real-base e2e размечены integration и исключены из coverage-замера
- [x] тесты переведены на E:\\tmp; C:/tmp/pytest-of-* очищен
- [x] ruff/mypy/pytest зелёные; релиз 0.33.0
