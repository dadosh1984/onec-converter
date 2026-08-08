// GREEN: формат 1Cv8.dt (8.x) — исследование/статус
import * as fs from 'node:fs';
import * as path from 'node:path';

export function spike_1cv8_dt_8_x_docs_format_8x_md() {
  const doc = path.resolve(process.cwd(), 'docs/format-8x.md');
  const section = `
### 1Cv8.dt (8.x) — статус исследования

Приоритет низкий: основной формат источника 8.x — живая файловая ИБ 1Cv8.1CD
(выгрузка .dt не нужна). Формат дампа 8.x проприетарный и отличается от 7.7
(не zlib-контейнер). При наличии реального .dt — разбор по логике сообщества
(tool1cd/onec_dtools), решение: переиспользовать 1CD-парсер после распаковки
или нет. Запасной коннектор source_8x_dt не реализован (честный статус: не исследован).
`;
  fs.mkdirSync(path.dirname(doc), { recursive: true });
  fs.appendFileSync(doc, section);
  return 'docs/format-8x.md: добавлен статус 1Cv8.dt';
}
