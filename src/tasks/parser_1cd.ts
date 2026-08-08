/**
 * parser-1cd — capability-экспорт изменения 1-8-x-1cv8.
 *
 * Изменение поставляет собственный парсер файловой ИБ 1С 8.x (1Cv8.1CD):
 * каталог таблиц (root/FAT level 0/1), строки с декодированием полей
 * (NVC=UTF-16LE, RV=GUID, N=BCD, DT=7 байт, L=1 байт), blob-цепочки 256 Б,
 * DBSCHEMA (типы, привязка таблица↔объект), конфигурация 8.1-эпохи (zlib),
 * оба стиля имён таблиц (_REFERENCE3 / _Reference74), интеграция в
 * read_metadata()/to_model(), status-тул в mcp_server.
 * Экспорт нужен для drift-сверки specs → src/tasks (см. orion shield).
 */
export function parser_1cd(): string {
  return [
    'onec_converter: собственный парсер 1Cv8.1CD (Фаза 5)',
    'source_8x_file.py: Database1CD, read_metadata, read_table, to_model',
    '8.1-эпоха: _REFERENCE3 (517 таблиц), 8.3: _Reference74 (8033 таблицы)',
    'escape \\dXXXX (суррогаты UTF-16) в скобкофайлах 8.3, DBNames-приоритет',
    'см. changes/1-8-x-1cv8/design.md и docs/format-8x.md',
  ].join('\n');
}

export { parser_1cd as "parser-1cd" };
