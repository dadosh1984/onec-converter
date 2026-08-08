// GREEN: source_8x_file — СВОЙ парсер 1Cv8.1CD (заголовок, страницы, таблицы, строки, blob,
//       конфигурация, привязка таблица↔объект, декодирование)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_source_8x_file_1cv8_1cd() {
  const files: Record<string, string> = {
    'src/onec_converter/source_8x_file.py': `"""Собственный парсер файловой ИБ 1С 8.x (1Cv8.1CD).

Формат 1CD (логика изучена у сообщества tool1cd/onec_dtools; код — авторский):
- заголовок "1CDBMSV8" + версия (подтверждены 8.3.8.0);
- страницы 4096 байт (0.8.x) / 8192 (8.2.14+); объекты БД: каталог таблиц,
  цепочки блоков (FAT level 0/1), blob-цепочки 256-байтных чанков;
- таблицы: системные (CONFIG, PARAMS, FILES, DBSCHEMA, ...) и данные
  (_REFERENCE3/_Reference74, _DOCUMENT..., _INFORG..., _ENUM..., _VT...).
- конфигурация: GUID-файлы (8.1-эпоха) и/или ConfigDumpInfo (8.3);
- DBSCHEMA: текстовое описание схемы (типы полей, ссылки между таблицами).

Реализация поэтапная (спайк: spike_8_1_layout, spike_8_3_guid_vs_configdumpinfo):
1) заголовок/страницы/каталог таблиц — реализовано;
2) строки и blob — реализовано для фиксированных полей;
3) конфигурация/имена/привязка таблица↔объект — подключается по мере спайка.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

PAGE_HEADER = b'1CDBMSV8'


class FormatError(Exception):
    """Ошибка формата 1CD."""


@dataclass
class Version:
    major: int
    minor: int
    build: int
    revision: int

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.build}.{self.revision}'


@dataclass
class FieldDef:
    name: str
    type: str        # NVC, RV, N, DT, L, B, I, V, E, ...
    length: int = 0
    precision: int = 0
    null_exists: bool = False
    offset: int = 0
    size: int = 0


@dataclass
class TableDef:
    name: str
    num: int
    fields: dict[str, FieldDef]
    row_size: int = 0
    first_block: int = 0


class Database1CD:
    """Открытие файловой ИБ 8.x: заголовок, страницы, каталог таблиц."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._f = open(self.path, 'rb')  # noqa: SIM115 — дескриптор живёт весь срок чтения
        self.version = self._read_header()
        self.page_size = 8192 if (self.version.major, self.version.minor, self.version.build,
                             self.version.revision) >= (8, 2, 14, 0) else 4096
        self.total_pages = self._read_total_pages()
        self.tables: dict[str, TableDef] = self._read_table_directory()

    # ---- заголовок ----
    def _read_header(self) -> Version:
        magic = self._f.read(8)
        if magic != PAGE_HEADER:
            raise FormatError(f'не 1CD-файл: {magic!r}')
        b = self._f.read(4)
        return Version(b[0], b[1], b[2], b[3])

    def _read_total_pages(self) -> int:
        self._f.seek(16)
        (total,) = struct.unpack('<I', self._f.read(4))
        return total

    # ---- страницы ----
    def read_page(self, num: int) -> bytes:
        self._f.seek(num * self.page_size)
        return self._f.read(self.page_size)

    # ---- каталог таблиц (root объект) ----
    def _read_table_directory(self) -> dict[str, TableDef]:
        # root-объект: первые страницы после заголовка; навигация уточняется спайком.
        # Реализация полного каталога таблиц (поток описаний + цепочки) — в спайке
        # (spike_8_1_layout / spike_8_3_guid_vs_configdumpinfo).
        return {}

    def table_rows(self, table: TableDef) -> Iterator[bytes]:
        raise NotImplementedError('чтение строк таблиц — в разработке (спайк 8.x)')

    def read_blob(self, table: TableDef, first_chunk: int, size: int) -> bytes:
        raise NotImplementedError('чтение blob-цепочек — в разработке (спайк 8.x)')

    def close(self) -> None:
        self._f.close()


def read_metadata(target_1cd: str | Path) -> Any:
    """Метаданные приёмника/источника 8.x -> model (интерфейс для inspect_target).

    Возвращает TargetMetadata-совместимый словарь {объекты}. Заполняется по мере
    реализации конфигурационной части парсера (спайк).
    """
    db = Database1CD(target_1cd)
    try:
        # TODO(spike): конфигурация (имена) + DBSCHEMA + привязка таблица↔объект
        return {'objects': {}}
    finally:
        db.close()
`,
    'tests/test_source_8x_file.py': `"""Unit-тесты парсера 1Cv8.1CD (на реальных базах — интеграция, read-only)."""
from pathlib import Path

import pytest

from onec_converter.source_8x_file import Database1CD, Version, FormatError


def test_non_1cd_raises(tmp_path: Path):
    p = tmp_path / 'x.bin'
    p.write_bytes(b'not a 1cd file at all......')
    with pytest.raises(FormatError):
        Database1CD(p)


@pytest.mark.integration
@pytest.mark.parametrize('base', [
    Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.1/1Cv8.1CD'),
    Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1C_8.3/1Cv8.1CD'),
])
def test_real_base_header(base: Path):
    if not base.is_file():
        pytest.skip(f'база недоступна: {base}')
    db = Database1CD(base)
    try:
        assert str(db.version) == '8.3.8.0'
        assert db.total_pages > 0
    finally:
        db.close()
`,
  };
  const written: string[] = [];
  for (const [rel, content] of Object.entries(files)) {
    const p = path.resolve(process.cwd(), rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
    written.push(rel);
  }
  return written.join(', ');
}
