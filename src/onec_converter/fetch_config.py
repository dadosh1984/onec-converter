"""fetch-config: релиз конфигурации как ИСТОЧНИК метаданных (Фаза 26).

Загрузка релиза конфигурации 1С из каталога XML-выгрузки (стандартный
«каталог поставки» — формат «Выгрузка в XML», корень Configuration.xml)
в единую модель {objects: [kind, name, uuid]} — сравнение/диагностика
структуры приёмника без платформы и без файловой ИБ.

Идея: arkuznetsov/yard (релизы конфигураций). Код авторский.

Двоичные .cf НЕ поддерживаются (формат контейнера не документирован;
используйте XML-выгрузку) — возвращается FetchConfigError с подсказкой.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from .audit import get_audit

# теги-контейнеры метаданных в Configuration.xml (вложены в ChildObjects)
_META_TAGS = frozenset({
    'Справочник', 'Документ', 'РегистрСведений', 'РегистрНакопления',
    'РегистрБухгалтерии', 'РегистрРасчета', 'Перечисление', 'Отчет',
    'Обработка', 'Константа', 'ПланСчетов', 'ПланВидовХарактеристик',
    'ПланОбмена', 'ПодпискаНаСобытие', 'РегламентноеЗадание',
    'Язык', 'Стиль', 'ОбщаяКартинка', 'ОбщийМодуль', 'ОбщийРеквизит',
    'ФункциональнаяОпция', 'Роль', 'ХранилищеНастроек',
    'ПакетXDTO', 'WebСервис', 'WSСсылка', 'HTTPСервис',
})

# Английские теги MDClasses (выгрузка конфигурации 1С: Catalog, Document...) -> русский kind
_META_TAGS_EN: dict[str, str] = {
    'Catalog': 'Справочник',
    'Document': 'Документ',
    'Constant': 'Константа',
    'Enum': 'Перечисление',
    'AccumulationRegister': 'РегистрНакопления',
    'InformationRegister': 'РегистрСведений',
    'AccountingRegister': 'РегистрБухгалтерии',
    'CalculationRegister': 'РегистрРасчета',
    'ChartOfAccounts': 'ПланСчетов',
    'ChartOfCharacteristicTypes': 'ПланВидовХарактеристик',
    'ChartOfCalculationTypes': 'ПланВидовРасчета',
    'ExchangePlan': 'ПланОбмена',
    'Report': 'Отчет',
    'DataProcessor': 'Обработка',
    'CommonModule': 'ОбщийМодуль',
    'SessionModule': 'МодульСеанса',
    'CommonAttribute': 'ОбщийРеквизит',
    'CommonForm': 'ОбщаяФорма',
    'CommandGroup': 'ГруппаКоманд',
    'Command': 'Команда',
    'Role': 'Роль',
    'Subsystem': 'Подсистема',
    'EventSubscription': 'ПодпискаНаСобытие',
    'ScheduledJob': 'РегламентноеЗадание',
    'Language': 'Язык',
    'Style': 'Стиль',
    'StyleItem': 'ЭлементСтиля',
    'CommonPicture': 'ОбщаяКартинка',
    'FunctionalOption': 'ФункциональнаяОпция',
    'WebService': 'WebСервис',
    'HTTPService': 'HTTPСервис',
    'XDTOPackage': 'ПакетXDTO',
    'SettingsStorage': 'ХранилищеНастроек',
    'FilterCriterion': 'КритерийОтбора',
    'CommonTemplate': 'ОбщийМакет',
    'DefinedType': 'ОпределяемыйТип',
}


class FetchConfigError(Exception):
    """Ошибка загрузки релиза конфигурации."""


def parse_configuration_xml(source: str | Path) -> dict[str, object]:
    """Разобрать XML-выгрузку конфигурации -> {objects, source}.

    objects: [{kind, name, uuid}] — объекты верхнего уровня из
    MetaDataObject/Configuration/ChildObjects (каталог поставки).
    kind — русское имя вида (Справочник/Документ/...): принимаются и
    русские теги, и английские теги MDClasses (Catalog/Document/Constant...).
    """
    src = Path(source)
    if not src.is_dir():
        raise FetchConfigError(f'каталог поставки не существует: {source}')
    cfg_xml = src / 'Configuration.xml'
    if not cfg_xml.is_file():
        raise FetchConfigError(
            f'нет Configuration.xml в {source} (нужна XML-выгрузка 1С; '
            'двоичные .cf не поддерживаются)')
    try:
        root = ET.parse(cfg_xml).getroot()
    except ET.ParseError as exc:
        raise FetchConfigError(f'Configuration.xml повреждён: {exc}') from exc

    objects: list[dict[str, object]] = []

    def walk(node: ET.Element) -> None:
        for child in node:
            kind = child.tag.split('}')[-1]
            ru_kind = _META_TAGS_EN.get(kind, kind)
            if ru_kind in _META_TAGS:
                uuid = child.attrib.get('uuid', '')
                name = ''
                for props in child.iter():
                    if props.tag.split('}')[-1] == 'Name' and props.text:
                        name = props.text
                        break
                objects.append({'kind': ru_kind, 'name': name, 'uuid': uuid})
            walk(child)

    for child in root:
        tag = child.tag.split('}')[-1]
        if tag in ('MetaDataObject', 'Configuration'):
            walk(child)
    return {'ok': True, 'objects': objects,
            'source': str(src), 'total': len(objects)}


def fetch_config(source: str | Path, out_file: str = '') -> dict[str, object]:
    """Обёртка: релиз конфигурации -> модель метаданных; out_file — JSON.

    Журнал аудита: INFO-событие fetch-config."""
    rep = parse_configuration_xml(source)
    if out_file:
        Path(out_file).write_text(
            json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    get_audit().info('fetch-config', obj=str(source),
                     result='ok', detail=str(rep['total']))
    return rep
