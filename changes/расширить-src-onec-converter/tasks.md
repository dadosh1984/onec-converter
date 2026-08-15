# Задачи — расширить-src-onec-converter

Расширить `fetch-config` (parse_configuration_xml) под английские теги MDClasses
(Catalog/Document/Constant...), сохранив русские. Ворота: pytest, mypy strict,
ruff, vitest; без новых зависимостей.

- [x] [fact] Маппинг англ.→рус. тегов метаданных в fetch_config.py (`_META_TAGS_EN`):
      Catalog→Справочник, Document→Документ, Constant→Константа, Enum→Перечисление,
      AccumulationRegister→РегистрНакопления, InformationRegister→РегистрСведений,
      AccountingRegister→РегистрБухгалтерии, CalculationRegister→РегистрРасчета,
      ChartOfAccounts→ПланСчетов, ChartOfCharacteristicTypes→ПланВидовХарактеристик,
      ChartOfCalculationTypes→ПланВидовРасчета, ExchangePlan→ПланОбмена, Report→Отчет,
      DataProcessor→Обработка, CommonModule→ОбщийМодуль, CommonAttribute→ОбщийРеквизит,
      CommonForm→ОбщаяФорма, CommandGroup→ГруппаКоманд, Command→Команда, Role→Роль,
      Subsystem→Подсистема, EventSubscription→ПодпискаНаСобытие, ScheduledJob→РегламентноеЗадание,
      Language→Язык, Style→Стиль, StyleItem→ЭлементСтиля, CommonPicture→ОбщаяКартинка,
      FunctionalOption→ФункциональнаяОпция, WebService→WebСервис, HTTPService→HTTPСервис,
      XDTOPackage→ПакетXDTO, SettingsStorage→ХранилищеНастроек, FilterCriterion→КритерийОтбора,
      CommonTemplate→ОбщийМакет, DefinedType→ОпределяемыйТип, SessionModule→МодульСеанса
- [x] [fact] `parse_configuration_xml` распознаёт английские теги: kind в objects —
      русское имя из маппинга (не сырой тег); name/uuid — как раньше; юнит-тест:
      синтетический XML `<Catalog uuid=...><Name>Банки</Name>`, `<Document>`, `<Constant>`
      -> objects c kind 'Справочник'/'Документ'/'Константа', total корректный
- [x] [fact] Совместимость: русские теги по-прежнему работают (существующий тест
      test_fetch_config.py не сломан); юнит-тест: XML с `<Справочник>` -> kind 'Справочник'
- [x] [fact] Обход вложенных контейнеров: объекты ищутся не только на верхнем уровне
      MetaDataObject, но и внутри Configuration/ChildObjects (walk уже рекурсивный —
      зафиксировать тестом на вложенной структуре)
- [x] [assumption] Тест на реальной выгрузке XML_8.1 (Configuration.xml: 62 Catalog,
      136 Document, 17 Constant): total >= 200, есть kind 'Справочник'/'Документ';
      skip, если каталога нет
- [x] [assumption] README/docs/commands-map: fetch-config поддерживает английские теги
      выгрузки (MDClasses)
