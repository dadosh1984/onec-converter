/**
 * load_direct — capability-экспорт изменения фаза-13-zero-setup.
 *
 * Фаза 13 (zero-setup, вариант A): прямая загрузка в 1CD без HTTP-расширения.
 *  - load_8x.py: object_to_row(table_def, field_map, obj, idref) — сборка
 *    строки таблицы 1CD из объекта после transform (NVC/NC/N/L/DT/B/RV);
 *  - load_direct(target_dir, objects, workdir) — копия приёмника (copy_1cd),
 *    группировка по таблицам (read_metadata: kind+name → _REFERENCE_n),
 *    append_records; оригинал не изменяется; LockError/WriteError наружу;
 *  - CLI `onec-converter load --direct <target-dir> --input <batch.json>`
 *    (альтернатива --http), MCP-тул load_direct;
 *  - docs: zero-setup.md (вариант A: MVP реализован), README, pipeline.md.
 */
export function load_direct() {
  return 'load_direct stub';
}
