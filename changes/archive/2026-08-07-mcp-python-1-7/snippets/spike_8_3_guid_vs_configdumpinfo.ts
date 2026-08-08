// GREEN: формат хранилища конфигурации 8.3 (GUID-файлы vs ConfigDumpInfo)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function spike_8_3_guid_vs_configdumpinfo() {
  const doc = path.resolve(process.cwd(), 'docs/format-8x.md');
  const section = `
### Хранилище конфигурации 8.3 — спайк

Приёмник 1C_8.3: 1CD 8.3.8.0, 8033 таблицы, конфигурация «Бухгалтерия для Узбекистана 3.0»
(DoNotCopy.txt), данных нет. Системные таблицы: CONFIG, CONFIGSAVE, PARAMS, FILES,
DEPOTFILES, CONFIGCAS, CONFIGCASSAVE, DBSCHEMA, SCHEMASTORAGE, V8CMSDPWDS.

Открытые вопросы:
- [ ] Именование файлов конфигурации в таблице CONFIG приёмника: GUID-файлы (8.1-эпоха)
      или единый ConfigDumpInfo (8.3); есть ли root/main.
- [ ] Совпадает ли layout дерева коллекций с 8.1-эпохой (класс-GUID + список GUID объектов).
- [ ] Требование к парсеру: поддерживать оба стиля хранилища конфигурации.
`;
  fs.mkdirSync(path.dirname(doc), { recursive: true });
  fs.appendFileSync(doc, section);
  return 'docs/format-8x.md: добавлен раздел хранилища конфигурации 8.3';
}
