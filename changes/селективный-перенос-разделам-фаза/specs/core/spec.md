# Spec: core

## Purpose
Реализовать селективный перенос по разделам (Фаза 29.2, требование пользователя) в onec-converter: extract --objects "Справочник.Номенклатура,Документ.БанковскиеВыписки" — фильтр по конфигурационным объектам (kind+имя из read_metadata), поддержка групп Справочник.*/Документ.*/Регистр.*, физические таблицы Таблица._REFERENCE3; без --objects — перенос всех данных (по умолчанию, совместимость). MCP step_extract — параметр objects. Новый модуль objects_filter.py (парсер+матчер), тесты (unit + CLI 8x на fake-базе + 7.7). Доки README/CHANGELOG. Ворота зелёные, релиз 0.6.0.

## Acceptance criteria
- [ ] Placeholder — refine during implementation
