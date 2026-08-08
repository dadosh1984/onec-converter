// GREEN: генератор фикстур — синтетический 1Cv77.dat (текстовый формат, CP866)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_1cv77_dat_cp866() {
  const files: Record<string, string> = {
    'tests/fixtures/gen_dat.py': `"""Генератор синтетического 1Cv77.dat (текстовый формат ИБ 1С 7.7, CP866).

Используется в unit-тестах: v77_reader должен разбирать файл, сгенерированный
этой функцией, и восстанавливать исходную структуру (round-trip).
"""

from __future__ import annotations

from typing import Any


def quote(value: Any) -> str:
    """Кавычки для строкового значения: удвоение кавычек внутри."""
    return '"' + str(value).replace('"', '""') + '"'


def fmt_value(value: Any) -> str:
    """Форматирование значения в терминал формата:
    строка -> "…", int/float -> число, None -> "" (пустая строка)."""
    if value is None:
        return '""'
    if isinstance(value, str):
        return quote(value)
    return str(value)


def fmt_record(record: list[Any]) -> str:
    return '{' + ','.join(fmt_value(v) for v in record) + '}'


def make_dat(
    unique_ids: dict[int, int] | None = None,
    constants: list[tuple[int, list[Any]]] | None = None,
    references: dict[int, list[list[Any]]] | None = None,
) -> bytes:
    """Собрать текст 1Cv77.dat и вернуть байты в CP866."""
    unique_ids = unique_ids or {1: 0}
    constants = constants or []
    references = references or {}

    parts: list[str] = []
    parts.append('{' + quote('7.70') + ',' + quote('') + ',')

    # System table — минимальный стенд (реальное содержимое не зафиксировано)
    parts.append('{' + quote('System table') + ',{0,0,' + quote('fixture') + '}},')

    inner = ','.join('{%d,%s}' % (tid, quote(f'{cnt}|')) for tid, cnt in sorted(unique_ids.items()))  # noqa: UP031
    parts.append('{' + quote('Unique IDs') + ',' + inner + '},')

    inner = ','.join('{%d,{%s}}' % (cid, ','.join(fmt_value(v) for v in vals))  # noqa: UP031
                     for cid, vals in constants)
    parts.append('{' + quote('Constants') + ',' + inner + '},')

    inner = ','.join('{%d,%s}' % (tid, ','.join(fmt_record(r) for r in recs))  # noqa: UP031
                     for tid, recs in references.items())
    parts.append('{' + quote('References') + ',' + inner + '},')

    parts.append('{' + quote('Template Operations') + ',{}},')
    parts.append('{' + quote('Correct Entries') + ',{}}')
    parts.append('}')
    return ''.join(parts).encode('cp866', errors='replace')
`,
    'tests/fixtures/__init__.py': ``,
    'tests/test_gen_dat.py': `"""Тесты генератора фикстур и round-trip с v77_reader."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.fixtures.gen_dat import make_dat, fmt_record
from onec_converter.v77_reader import V77Reader, parse_dat


def test_make_dat_encodes_cp866():
    data = make_dat(unique_ids={1: 2}, references={1: [["11|", "код1", "Имя1"]]})
    text = data.decode('cp866')
    assert '7.70' in text
    assert 'Unique IDs' in text


def test_roundtrip_parser():
    data = make_dat(
        unique_ids={1: 3, 2: 1},
        constants=[(7, ['0|', 20240101, '0|', 0, 0, 0, 100.50])],
        references={1: [['1|', '0001', 'Товар А'], ['2|', '0002', 'Товар Б']]},
    )
    reader = V77Reader.from_bytes(data)
    assert reader.unique_ids() == {1: 3, 2: 1}
    consts = reader.constants()
    assert consts[0][0] == 7
    refs = reader.references()
    assert refs[1][0] == ['1|', '0001', 'Товар А']


def test_parse_dat_scalars():
    text = '{"7.70","",{"A",{1,"2|",20240101,0.50}}}'
    root = parse_dat(text)
    assert root[0] == '7.70'
    assert root[2][1][2] == 20240101
    assert root[2][1][3] == 0.5
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
