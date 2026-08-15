# Предложение — расширить-src-onec-converter

## Цель
Расширить src/onec_converter/fetch_config.py (команда CLI fetch-config) в проекте onec_converter: сейчас parse_configuration_xml ищет в Configuration.xml только РУССКИЕ теги-контейнеры метаданных (_META_TAGS: Справочник, Документ, РегистрСведений и т.д.) и на выгрузках с АНГЛИЙСКИМИ тегами (Catalog, Document, Constant, Enum, AccumulationRegister и т.д. — формат MDClasses из выгрузки конфигурации 1С) возвращает objects=[], total=0. Задача: (1) добавить маппинг англ.→рус. тегов метаданных (Catalog→Справочник, Document→Документ, Constant→Константа, Enum→Перечисление, AccumulationRegister→РегистрНакопления, InformationRegister→РегистрСведений, AccountingRegister→РегистрБухгалтерии, CalculationRegister→РегистрРасчета, ChartOfAccounts→ПланСчетов, ChartOfCharacteristicTypes→ПланВидовХарактеристик, ChartOfCalculationTypes→ПланВидовРасчета, ExchangePlan→ПланОбмена, Report→Отчет, DataProcessor→Обработка, CommonModule→ОбщийМодуль, SessionModule→МодульСеанса, CommonAttribute→ОбщийРеквизит, CommonForm→ОбщаяФорма, CommandGroup→ГруппаКоманд, Command→Команда, Role→Роль, Subsystem→Подсистема, EventSubscription→ПодпискаНаСобытие, ScheduledJob→РегламентноеЗадание, Language→Язык, Style→Стиль, StyleItem→ЭлементСтиля, CommonPicture→ОбщаяКартинка, FunctionalOption→ФункциональнаяОпция, WebService→WebСервис, HTTPService→HTTPСервис, XDTOPackage→ПакетXDTO, SettingsStorage→ХранилищеНастроек, FilterCriterion→КритерийОтбора, CommonTemplate→ОбщийМакет, DefinedType→ОпределяемыйТип); (2) kind в objects должен быть русским именем (как было для русских тегов), имя объекта — из дочернего тега Name (уже есть); (3) искать объекты не только в корневом MetaDataObject, но и во вложенных Configuration/ChildObjects (уже есть walk — проверить, что он обходит вложенность); (4) unit-тесты на синтетическом XML с английскими тегами (Catalog с Name и uuid, Document, Constant) — total и kind/name/uuid корректны; (5) тест на реальной выгрузке XML_8.1 (62 Catalogs + 136 Documents + 17 Constants в Configuration.xml) — опционально, если папка есть, иначе skip; (6) mypy strict/ruff/pytest зелёные; README/docs commands-map: пометить fetch-config как поддерживающий англ. теги. Ворота: без новых зависимостей; только stdlib.

## Контекст

| Аспект | Значение |
|--------|----------|
| Платформа | Без новых зависимостей (только stdlib xml.etree). Ворота: pytest, mypy strict, ruff, vitest зелёные. Сохранить совместимость с русскими тегами. |
| Бюджет | compact |
| Ограничения | compact |

- **Lessons applied (v0.12):** скилл-onec-converter-migration:forge:56cc53ac3e99, фаза-11-новая-порция:forge:409e2a92d172, фаза-11-новая-порция:forge:537c39f668a9, mcp-python-1-7:forge:9c866da712f6, mcp-python-1-7:forge:d46606a68cf7
