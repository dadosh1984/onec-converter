// GREEN: source_8x_dt — чтение 1Cv8.dt (8.x): распаковка дампа
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_source_8x_dt_1cv8_dt_8_x_unit() {
  const files: Record<string, string> = {
    'src/onec_converter/source_8x_dt.py': `"""Чтение выгрузки 8.x (1Cv8.dt) — запасной коннектор.

Формат дампа 8.x проприетарный и отличается от 7.7 (не zlib-контейнер).
Исследование — задача spike_1cv8_dt_8_x_docs_format_8x_md (низкий приоритет:
основной формат источника 8.x — живая база 1Cv8.1CD).
"""

from __future__ import annotations

from pathlib import Path


class DtFormatError(Exception):
    """Ошибка формата 1Cv8.dt."""


def open_dt(dt_path: str | Path) -> object:
    """Открыть выгрузку 8.x (пока не реализовано — исследование не завершено)."""
    raise DtFormatError('формат 1Cv8.dt не исследован (см. docs/format-8x.md); '
                        'используйте файловую ИБ 1Cv8.1CD')
`,
    'tests/test_source_8x_dt.py': `"""Тесты коннектора .dt (8.x)."""
import pytest

from onec_converter.source_8x_dt import open_dt, DtFormatError


def test_open_dt_not_implemented(tmp_path):
    with pytest.raises(DtFormatError):
        open_dt(tmp_path / 'x.dt')
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
