# Spec: cli_py_argparse

## Purpose

Фаза 9: CLI-обёртка для onec_converter (перенос данных между ИБ 1С) без
MCP-клиента — команды прямо в терминале. Только stdlib (argparse), без
новых зависимостей. CLI переиспользует существующий пайплайн
(mcp_server.py: step_init/step_inspect_source/step_extract/step_inspect_target/
step_map/step_prevalidate/step_load/step_status) и коннекторы
(Base77/v77_reader, source_8x_file/source_8x_dt), transform, validate, verify.

## Capabilities

### cli-обёртка (cli.py)

- Подкоманды `inspect`, `extract`, `map`, `transform`, `load`, `status`
  через argparse-субпарсеры (stdlib, без новых зависимостей).
- Общий контекст: `--project-dir`, `--source-dir`, `--source-encoding`
  (дефолт cp866 — для 7.7).
- Entry-point `onec-converter` в pyproject → `onec_converter.cli:main`.

### inspect

- Метаданные источника: объекты, виды, таблицы, размеры
  (переиспользует разведку коннекторов и table_sizes).

### extract

- Чтение 7.7/8.x → intermediate JSON (UTF-8, ensure_ascii=False, indent=2).
- Флаги: `--out`, `--encoding`, `--anonymize-fields`, `--limit`, `--objects`.

### map

- `--rules-file`: валидация TOON-правил (сообщение ok/ошибки, exit code).
- `--llm-prompt`: формирование промпта для LLM из метаданных,
  вывод в файл, БЕЗ вызова LLM.

### transform

- Применение правил к intermediate JSON: `--rules-file`, `--out`.
- `--preview`: dry-run — первые N строк на объект, без записи.

### load

- Загрузка батчей в приёмник: file (каталог/JSON) или HTTP base_url
  расширения 8.3.
- Ретраи + отчёт об ошибках (какие батчи/объекты не загружены).

### status

- Состояние пайплайна в project-dir: коннекторы, кеш, последний шаг,
  метрики (как MCP pipeline_status).

## Acceptance criteria

- [ ] `onec-converter --help` показывает подкоманды inspect/extract/map/
      transform/load/status; неверная подкоманда → exit 2
- [ ] `onec-converter extract --source-dir <7.7 база> --out out.json`
      создаёт intermediate JSON; `--limit`, `--anonymize-fields`,
      `--objects` работают
- [ ] `onec-converter map --llm-prompt --meta-source ms.json
      --meta-target mt.json --out prompt.txt` пишет промпт без вызова LLM;
      `--rules-file` с невалидными правилами → ошибка + exit 1
- [ ] `onec-converter transform --rules-file rules.json --preview`
      показывает первые строки без записи; без `--preview` пишет `--out`
- [ ] `onec-converter load --target <file|http>` загружает батчи,
      ретраи и отчёт об ошибках; успех → exit 0
- [ ] `onec-converter status --project-dir <dir>` выводит JSON-состояние
      пайплайна (как pipeline_status)
- [ ] pyproject содержит entry-point `onec-converter`; `onec-converter
      --version` работает (0.1.0)
- [ ] Unit-тесты CLI (прямой вызов main + subprocess smoke) зелёные;
      pytest / mypy strict / ruff / vitest — без ошибок
- [ ] README содержит раздел CLI с примерами каждой подкоманды
