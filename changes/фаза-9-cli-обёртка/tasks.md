# Tasks — фаза-9-cli-обёртка

CLI-обёртка пайплайна без MCP-клиента. Пайплайн уже есть в mcp_server.py
(step_init/step_inspect_source/step_extract/step_inspect_target/step_map/
step_prevalidate/step_load/step_status) — CLI переиспользует его,
не дублируя логику. Только stdlib (argparse), entry-point в pyproject.

- [x] [fact] `cli.py`: argparse-подкоманды `inspect`, `extract`, `map`,
      `transform`, `load`, `status`; общий контекст `--project-dir`,
      `--source-dir`, `--source-encoding` (cp866 для 7.7)
- [x] [assumption] `inspect`: метаданные источника (объекты, виды, таблицы,
      размеры) — переиспользовать разведку коннекторов + table_sizes
- [x] [assumption] `extract`: чтение 7.7/8.x → intermediate JSON
      (`--out`, `--encoding`, `--anonymize-fields`, `--limit`, `--objects`)
- [x] [assumption] `map`: `--rules-file` (валидация TOON-правил) и
      `--llm-prompt` (вывод промпта в файл, без вызова LLM)
- [x] [assumption] `transform`: применение правил к intermediate
      (`--rules-file`, `--out`, `--preview` dry-run)
- [x] [assumption] `load`: загрузка батчей в приёмник
      (file/HTTP base_url) с ретраями и отчётом об ошибках
- [x] [assumption] `status`: состояние пайплайна в project-dir
      (коннекторы, кеш, последний шаг, метрики)
- [x] [fact] pyproject: entry-point `onec-converter`; unit-тесты CLI
      (прямой вызов main + subprocess smoke entry-point)
- [x] [assumption] README: раздел CLI с примерами каждой подкоманды

Ворота: pytest, mypy strict, ruff, vitest (Orion shield). Реальные базы —
read-only, только stdlib для CLI (argparse), без новых зависимостей.
