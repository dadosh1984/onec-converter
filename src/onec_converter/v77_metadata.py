"""Парсер метаданных ИБ 1С 7.7 (1Cv7.MD, OLE2-контейнер).

Обход compound-документа через olefile: top-level storage (AccountChart, Document,
CalcVar, Subconto, ...), объекты конфигурации (storage 'Document_Number1015'),
потоки Container.Contents / WorkBook / MD Programm text.

Внутренний формат потока Container.Contents расшифровывается в спайке
(задача spike_1cv7_md_ole2_olefile); здесь — структурный доступ к дереву,
разбор сериализованных определений подключается после спайка.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import olefile


class MetadataError(Exception):
    """Ошибка чтения 1Cv7.MD."""


@dataclass
class ObjectDef:
    """Описание объекта конфигурации 7.7 (минимальное, уточняется спайком)."""

    storage: str
    number: str
    contents: bytes


class V77Metadata:
    """Доступ к OLE2-дереву 1Cv7.MD."""

    def __init__(self, md_path: str | Path):
        self.path = Path(md_path)
        try:
            self._ole = olefile.OleFileIO(str(self.path))
        except Exception as exc:
            raise MetadataError(f'не удалось открыть 1Cv7.MD: {exc}') from exc

    def close(self) -> None:
        try:
            self._ole.close()
        except Exception:  # noqa: BLE001, S110
            pass  # закрытие уже выполненное — не ошибка

    def top_storages(self) -> list[str]:
        """Имена storage верхнего уровня."""
        return sorted({p[0] for p in self._ole.listdir()})

    def listdir(self, storage: str = '') -> list[list[str]]:
        """Все entry внутри storage (рекурсивно), как список путей."""
        return [p for p in self._ole.listdir() if p[0] == storage]

    def object_storages(self) -> list[ObjectDef]:
        """Storage объектов конфигурации вида 'Тип_NumberNNNN' с потоком Container.Contents."""
        out: list[ObjectDef] = []
        for entry in self._ole.listdir():
            # объект: [Тип, Тип_NumberNNNN, Container.Contents]
            if len(entry) >= 3 and entry[-1] == 'Container.Contents':
                storage = entry[1]
                m = storage.rsplit('_', 1)
                number = m[1] if len(m) == 2 else ''
                try:
                    data = self._ole.openstream(entry).read()
                except Exception:  # noqa: BLE001
                    data = b''
                out.append(ObjectDef(storage=storage, number=number, contents=data))
        return out

    def streams(self, storage: str) -> list[str]:
        """Имена потоков внутри storage."""
        prefix = storage + '/'
        return sorted('/'.join(e) for e in self._ole.listdir() if '/'.join(e).startswith(prefix))
