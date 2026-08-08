# Spec: load_direct

## Purpose

Фаза 13 (zero-setup, вариант A): прямая загрузка данных в приёмник 8.x
без HTTP-расширения — напрямую в КОПИЮ `1Cv8.1CD` через write_8x
(Фазы 10–12). Оригинал никогда не изменяется.

## Capabilities

### object_to_row (load_8x.py)

- Сборка строки таблицы 1CD из объекта после transform: `_VERSION`,
  `_IDRREF` (16 байт), `_MARKED`, `_CODE`/`_DESCRIPTION` из key/атрибутов,
  атрибуты по field_map (русское имя → физическое поле).
- Кодирование по типам FieldDef: NVC/NC/N/L/DT/B/RV (как fake_1cd).

### load_direct (load_8x.py)

- Копия приёмника (`copy_1cd` в workdir) → группировка объектов по
  таблицам (read_metadata: kind+name → `_REFERENCE_n`) → `append_records`
  → статистика {copy_path, total, tables}.
- `_IDRREF`: префикс (первые 4 байта) из первой непустой строки таблицы
  или нули + уникальные 12 байт.
- LockError/WriteError наружу; оригинал не изменяется.

## Acceptance criteria

- [ ] object_to_row: все типы полей (unit), _IDRREF уникальны
- [ ] load_direct: копия приёмника + append → парсер читает (unit на
      синтетике; integration на КОПИИ реальной 1C_8.1, verify число строк)
- [ ] CLI `load --direct` и MCP `load_direct` работают
- [ ] docs: zero-setup.md (MVP реализован), README, pipeline.md
- [ ] Ворота: pytest (вкл. integration) / mypy strict / ruff / vitest
