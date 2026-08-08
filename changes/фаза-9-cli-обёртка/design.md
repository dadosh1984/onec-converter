# Design — фаза-9-cli-обёртка

## Overview

CLI-обёртка пайплайна onec_converter без MCP-клиента: команды прямо
в терминале. Только stdlib (argparse), без новых зависимостей.
CLI не дублирует логику MCP-сервера — переиспользует существующие модули:
пайплайн-класс (mcp_server.py, step_init/step_inspect_source/step_extract/
step_inspect_target/step_map/step_prevalidate/step_load/step_status),
transform, validate, verify, коннекторы Base77 / source_8x_file / source_8x_dt.

## Модули

- `src/onec_converter/cli.py` — точка входа (argparse, stdlib):
  - общий контекст: `--project-dir`, `--source-dir`, `--source-encoding`
    (дефолт cp866 для 7.7), `--log-level`;
  - подкоманды: `inspect`, `extract`, `map`, `transform`, `load`, `status`;
  - `inspect` — метаданные источника: объекты, виды, таблицы, размеры
    (переиспользует разведку: source_8x_file / v77_reader + table_sizes);
  - `extract` — чтение 7.7/8.x → intermediate JSON
    (`--out` (JSON-файл), `--encoding`, `--anonymize-fields`, `--limit`,
    `--objects` — фильтр по объектам);
  - `map` — генерация/валидация TOON-правил: `--rules-file` (валидация
    существующих), `--llm-prompt` (вывод промпта для LLM в stdout/файл,
    БЕЗ вызова LLM), `--meta-source` / `--meta-target` (JSON метаданных);
  - `transform` — применение правил к intermediate: `--rules-file`,
    `--out`, `--preview` (dry-run: первые N строк на объект, без записи);
  - `load` — загрузка батчей в приёмник: `--target` (файл/каталог JSON
    для file-режима или base_url HTTP-расширения 8.3), `--http` (режим
    HTTP), ретраи + отчёт об ошибках;
  - `status` — состояние пайплайна (project-dir): коннекторы, кеш,
    последний шаг, метрики (как pipeline_status в MCP).
- `src/onec_converter/__init__.py` — без изменений (пакет уже есть).
- `pyproject.toml` — entry-point `onec-converter = onec_converter.cli:main`.
- `tests/test_cli.py` — unit-тесты (прямой вызов main() с monkeypatch
  sys.argv + capsys, плюс subprocess для smoke entry-point).

## Решения

- Один модуль cli.py, подкоманды через `add_subparsers`; каждая подкоманда
  вызывает существующую функцию/класс пайплайна, а не копирует логику.
- Пайплайн-класс (mcp_server.py) уже принимает project_dir и держит
  состояние; CLI создаёт экземпляр так же, как MCP-сервер.
- `map --llm-prompt`: без внешних зависимостей LLM — только формирование
  промпта из метаданных (как в MCP-шаге step_map, но вывод вместо вызова).
- Кодировки: cp866/cp1251 для 7.7, UTF-8 для intermediate JSON
  (ensure_ascii=False, indent=2).
- Ошибки: argparse-ошибки → exit 2, ошибки пайплайна → сообщение в stderr
  и exit 1; успех — exit 0. Вывод данных — в stdout (машиночитаемо: JSON
  для status/extract summary), лог — в stderr.
- README: раздел CLI с примерами каждой подкоманды.

## Assumptions

- [ ] [fact] cli.py: argparse-подкоманды inspect/extract/map/transform/load/status
      + общий контекст (--project-dir, --source-dir, --source-encoding)
- [ ] [assumption] extract: 7.7/8.x → intermediate JSON
      (--encoding, --anonymize-fields, --limit, --objects)
- [ ] [assumption] map: --rules-file (валидация) и --llm-prompt (промпт
      без вызова LLM)
- [ ] [assumption] transform: --rules-file + --preview (dry-run)
- [ ] [assumption] load: file/HTTP с ретраями и отчётом об ошибках
- [ ] [fact] pyproject: entry-point onec-converter; unit-тесты CLI
      (прямой вызов main + subprocess smoke)
- [ ] [assumption] README: раздел CLI с примерами

## Verification

- [ ] pytest (все тесты, включая новые unit CLI)
- [ ] mypy src (strict)
- [ ] ruff check src tests
- [ ] npx vitest run (Orion shield)
