// GREEN: исследование внутреннего формата 1Cv7.MD (OLE2): Container.Contents, дерево объектов
import * as fs from 'node:fs';
import * as path from 'node:path';

export function spike_1cv7_md_ole2_olefile() {
  const doc = path.resolve(process.cwd(), 'docs/format-77.md');
  const section = `
### Спайк: внутренний формат 1Cv7.MD (продолжение)

Известно (первичный анализ реальной базы):
- 19 top-level storage: AccountChart, AccountChartList, CalcJournal, CalcVar,
  Container.Contents, Document, GlobalData, Journal, Metadata, Operation, OperationList,
  Picture, ProvList, Report, SubFolder, SubList, Subconto, TypedText, UserDef.
- Объекты конфигурации — storage \`Document/Document_Number1015\`,
  \`CalcVar/CalcVar_Number2451\`, \`Subconto/Subconto_Number354\`; внутри — потоки
  \`Container.Contents\` (сериализованный объект), \`WorkBook\`, \`Dialog Stream\`,
  \`MD Programm text\`, \`Page.N\`, \`Container.Profile\`, \`Commands\`.

Открытые вопросы (решаются скриптом в .spike на реальной базе):
- [ ] Внутренний формат потока \`Container.Contents\` (сериализация дерева объектов:
      имя, вид, реквизиты, типы, точность).
- [ ] Где лежат описания справочников и реквизитов (storage \`Metadata\`/\`GlobalData\`).
- [ ] Маппинг «секция/таблица 1Cv77.dat ↔ объект MD» (Unique IDs → имена объектов).
`;
  fs.mkdirSync(path.dirname(doc), { recursive: true });
  fs.appendFileSync(doc, section);
  return 'docs/format-77.md: добавлен раздел спайка 1Cv7.MD';
}
