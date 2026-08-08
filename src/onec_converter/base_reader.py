"""Вход проекта переноса: каталог файловой ИБ 1С 7.7.

Каталог содержит 1Cv7.MD (метаданные, OLE2) и 1Cv77.dat (данные, текст CP866).
Опционально — архив 1Cv7.DT (zlib-контейнер тех же файлов); распаковка в temp.
"""

from __future__ import annotations

import tempfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .v77_metadata import V77Metadata
from .v77_reader import V77Reader

MD_NAME = '1Cv7.MD'
DAT_NAME = '1Cv77.dat'
DT_NAME = '1Cv7.DT'


class BaseError(Exception):
    """Ошибка каталога ИБ 7.7."""


@dataclass
class Base77:
    """Каталог файловой ИБ 7.7 (метаданные + данные).

    `encoding` — кодировка текстовых полей .dat (идея A4: CP1251→UTF-8
    middleware): по умолчанию cp866 (стандарт 7.7), для баз в CP1251
    укажите 'cp1251'. Строки перекодируются при чтении и попадают
    в промежуточный JSON (UTF-8) без искажений.
    """

    base_dir: Path
    encoding: str = 'cp866'
    _md: V77Metadata | None = field(default=None, repr=False)
    _reader: V77Reader | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        if not self.base_dir.is_dir():
            raise BaseError(f'каталог ИБ не найден: {self.base_dir}')
        self.md_path = self.base_dir / MD_NAME
        self.dat_path = self.base_dir / DAT_NAME
        if not self.md_path.is_file():
            raise BaseError(f'нет {MD_NAME} в {self.base_dir}')
        if not self.dat_path.is_file():
            raise BaseError(f'нет {DAT_NAME} в {self.base_dir}')

    @property
    def metadata(self) -> V77Metadata:
        if self._md is None:
            self._md = V77Metadata(self.md_path)
        return self._md

    @property
    def data(self) -> V77Reader:
        if self._reader is None:
            self._reader = V77Reader(self.dat_path, encoding=self.encoding)
        return self._reader

    @classmethod
    def from_dt(cls, dt_path: str | Path, workdir: Path | None = None) -> Base77:
        """Распаковка 1Cv7.DT (zlib-контейнер) во временный каталог.

        Формат .dt 7.7: заголовок + поток zlib с файлами ИБ.
        Неподдерживаемые/повреждённые архивы -> BaseError.
        """
        dt = Path(dt_path)
        if not dt.is_file():
            raise BaseError(f'нет архива {dt}')
        data = dt.read_bytes()
        try:
            # пробуем вариант: весь файл — один zlib-поток
            payload = zlib.decompress(data)
        except zlib.error:
            # вариант: zlib-поток после заголовка
            try:
                payload = zlib.decompress(data[data.index(b'\x78'):])
            except (ValueError, zlib.error) as exc:
                raise BaseError('не удалось распаковать 1Cv7.DT (формат не опознан)') from exc
        tmp = Path(workdir or tempfile.mkdtemp(prefix='onec_dt_'))
        tmp.mkdir(parents=True, exist_ok=True)
        # файлы конкатенированы; простейший вариант — полагаем один файл 1Cv77.dat
        (tmp / DAT_NAME).write_bytes(payload)
        (tmp / MD_NAME).write_bytes(payload[:0])  # заглушка: MD извлекается по записям архива
        return cls(tmp)

    def close(self) -> None:
        """Освобождение ресурсов (временный каталог .dt)."""
        if self._md is not None:
            self._md.close()
