// GREEN: подтверждение секций 1Cv77.dat и грамматики значений
import * as fs from 'node:fs';
import * as path from 'node:path';

export function spike_1cv77_dat_system_table_unique_ids_constants_references() {
  const doc = path.resolve(process.cwd(), 'docs/format-77.md');
  const section = `
### Спайк: грамматика 1Cv77.dat (подтверждено на реальной базе)

Порядок секций верхнего уровня:
\`{"7.70","" → System table → Unique IDs → Constants → References →
документы/журналы/регистры → Template Operations → Correct Entries}\`.

Терминалы (для парсера v77_reader):
- строка: \`"…"\`, кавычки внутри удваиваются \`""\`;
- число: без кавычек, десятичная точка (0.00, 679330.00);
- дата: \`YYYYMMDD\` без кавычек (20241204);
- ссылка: \`"NNN|"\` (внутренний числовой ID), пустая — \`"0|"\`;
- Unique IDs: \`{id_таблицы, "счётчик|"}\` (напр. \`{81,"312|"}\`);
- запись справочника: \`{"193|","0|","  221","","0|",0,0,"00959","","",""}\`
  (ID записи, служебные, код фиксированной ширины с ведущими пробелами, имя, ...).

Открытые вопросы:
- [ ] Точная разметка кортежей документов/журналов/регистров (позиции реквизитов).
- [ ] Вложенные \`{"Actions"}\`/\`{"Accounting"}\` внутри операций.
`;
  fs.mkdirSync(path.dirname(doc), { recursive: true });
  fs.appendFileSync(doc, section);
  return 'docs/format-77.md: добавлена грамматика 1Cv77.dat';
}
