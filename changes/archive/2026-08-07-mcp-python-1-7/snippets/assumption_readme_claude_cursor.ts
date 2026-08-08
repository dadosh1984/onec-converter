// GREEN: README — установка, коннекторы, использование через Claude/Cursor, ограничения
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_readme_claude_cursor() {
  const files: Record<string, string> = {
    'README.md': `# onec-converter — MCP-сервер переноса данных между ИБ 1С

Авторский проект (код пишется с нуля; чужие проекты — только источник идей о форматах).

## Возможности
- Перенос данных **из любой версии ИБ 1С** (7.7, 8.1, 8.2, 8.3) в **1С 8.x** (основной
  приёмник — 8.3) по командам LLM-агентов (Claude, Cursor).
- Работает **без платформы 1С** (Windows/Linux/macOS).
- Источники: 7.7 — каталог ИБ (\`1Cv7.MD\` + \`1Cv77.dat\`, текстовый формат, CP866);
  8.x — файловая ИБ \`1Cv8.1CD\` (собственный парсер).
- Пайплайн: init → inspect_source → extract → inspect_target → map → transform →
  prevalidate → preview → load → **verify** (сверка полноты 100%).
- Правило **«1→1»**: одна передающая ИБ = одна принимающая ИБ.
- **Кеш** метаданных/данных: повторный анализ базы 2–3 ГБ не перечитывает её целиком.
- Промежуточный формат: XML/JSON + человекочитаемый xlsx-отчёт.

## Установка
\`\`\`
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows
.venv/bin/pip install -e ".[dev]"        # Linux/macOS
\`\`\`

## Подключение к Claude / Cursor
Пропишите MCP-сервер (stdio):
\`\`\`
mcp: python -m onec_converter.mcp_server
\`\`\`

## Порядок переноса (команды агенту)
1. «Подготовь проект переноса: источник <путь>, приёмник <путь>» — init (правило 1→1).
2. «Изучи источник» — inspect_source (метаданные).
3. «Выгрузи справочник Номенклатура» — extract (+ xlsx-отчёт).
4. «Изучи приёмник» — inspect_target (через /metadata или 1Cv8.1CD приёмника).
5. «Составь правила переноса» — map (LLM по метаданным обеих сторон).
6. «Проверь перенос» — transform + prevalidate (количество, ссылки, дубликаты).
7. «Перенеси» — preview → load (пакетная запись через HTTP-сервис расширения).
8. «Проверь полноту» — verify (сверка источник ↔ приёмник).

## Приёмник 8.3 (временно — расширение)
Установите расширение \`onec_loader\` (см. \`src/onec_converter/extension_83/README.md\`):
HTTP-сервисы \`GET /metadata\` и \`POST /load\`. Целевая фича «zero-setup» —
прямая запись в \`1Cv8.1CD\` (research: \`docs/zero-setup.md\`).

## Ограничения (MVP)
- Справочники и документы без табличных частей (далее: табличные части, перечисления,
  регистры).
- Расширение приёмника собирается в 1С:Предприятие (до фичи zero-setup).
- 1Cv8.dt и серверные ИБ (SQL) — запасные/не реализованы.

## Тесты
\`\`\`
pytest                      # unit + интеграционные (реальные базы — read-only копии)
ruff check src tests
mypy src
\`\`\`

## Документация форматов
- \`docs/format-77.md\` — текстовый формат ИБ 7.7 (\`1Cv77.dat\`, \`1Cv7.MD\`).
- \`docs/format-8x.md\` — формат \`1Cv8.1CD\` (1CD 8.3.8.0), конфигурация, DBSCHEMA.
- \`docs/zero-setup.md\` — фича минимального вмешательства на приёмнике.
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
