# Задачи — onec-converter-новый-режим

Простой путь: один новый модуль-оркестратор `user_data_migrate.py` +
классификатор `classify.py` поверх СУЩЕСТВУЮЩИХ команд (clone-db, bridge-export,
bridge-import, bridge-verify). Ничего нового без необходимости.

- [x] [fact] Классификация объектов ИБ источник: категории user/formula/service
      по типу объекта 1С (Справочник/Документ/Константа/РегистрСведений → user;
      Отчет/Обработка/Регистры-результаты (Накопления/Бухгалтерии/Расчета) → formula;
      ПланСчетов/Перечисление/ОбщийМодуль/служебные → service). Модуль classify.py,
      функция classify_objects(meta: dict) -> dict[str, str]; юнит-тест на
      синтетическом meta из test_bridge_e2e
- [x] [fact] План переноса: build_plan(meta, classify_result) -> список разделов
      {name, category, file} — только user-объекты; тест: plan содержит
      Справочник.Контрагенты, не содержит Отчет.*
- [x] [fact] Проверка путей + копия ТОЛЬКО приёмника в workdir: check_paths(src, tgt)
      (оба каталога существуют, src != tgt, в обоих 1Cv8.1CD) и clone_db(tgt, workdir/target_copy);
      тест на двух fake-базах (write_fake_1cd)
- [x] [fact] Экспорт user-разделов в xlsx-мост по одному файлу (export_bridge),
      итог: количество файлов; тест на fake-базе: 2 user-объекта -> 2 .xlsx
- [x] [fact] Загрузка по одному файлу в КОПИЮ приёмника (import_bridge) + обратный тест
      (verify_roundtrip): отчёт {ok, matched, mismatched, missing, extra};
      цикл повторяется до ok=True; e2e-тест: источник -> копия приёмника -> verify ok
- [x] [assumption] CLI-команда bridge-migrate: --source-dir, --target-dir, --workdir,
      --objects (фильтр) — оркестрация шагов 1-5; тест build_parser
- [x] [assumption] README + docs/commands-map.md: документировать bridge-migrate
