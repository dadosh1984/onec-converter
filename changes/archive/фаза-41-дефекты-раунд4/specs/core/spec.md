# Spec: core

## Purpose
Закрыть хирургические дефекты раунда 4 внешнего анализа: рассинхрон
OpenAPI-спеки с кодом, мёртвая докстрока ротации audit, дыра в проверке
корня hash-цепочки, SQL-инъекция через имя таблицы. Версия 0.24.0.

## Acceptance criteria
- [x] gen_openapi: version берётся из onec_converter.__version__
      (docs/openapi.yaml показывает 0.24.0)
- [x] gen_openapi: BearerAuth на /metadata и /load (оба хендлера зовут
      ПроверитьКлюч); регенерация спеки идентична закоммиченной
- [x] audit._rotate(): первая строка нового файла — маркер
      {"marker":"rotated","ts","prev_hash","hash"}; prev_hash = хеш
      последней записи старого файла (архив .1)
- [x] verify_audit(): первая запись без маркера с непустым prev_hash —
      нарушение (подмена корня детектируется)
- [x] sql_source.fetch_rows(): валидация [A-Za-z_][A-Za-z0-9_]* и кавычки
      ("name" / [name]); недопустимое имя -> SqlSourceError без запроса
- [x] sql_source MSSQL col_sql: AND (LIKE ... OR ...) + ESCAPE '\\'
- [x] Тесты: openapi version==__version__; регенерация идентична;
      golden-ротация (маркер+архив+продолжение+verify_audit);
      подмена prev_hash первой записи; sql-инъекция
- [x] Ворота: pytest (+7), conformance, ruff, mypy (51), check_bsl,
      vitest — зелёные; релиз 0.24.0
