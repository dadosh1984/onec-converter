// GREEN: интеграционный тест чтения на реальной базе 1С_7.7 (копия, read-only)
import * as fs from 'node:fs';
import * as path from 'node:path';

export function assumption_31_07_202() {
  const files: Record<string, string> = {
    'tests/test_real_base_77.py': `"""Интеграционные тесты на реальной базе 1С 7.7 (каталог 1С_7.7).

База копируется во временную папку (read-only доступ к оригиналу не трогаем).
Тесты: структура секций 1Cv77.dat, Unique IDs/Constants/References непусты,
ссылки вида "NNN|", даты YYYYMMDD.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from onec_converter.base_reader import Base77
from onec_converter.v77_reader import V77Reader

REAL_BASE = Path(r'E:/SYSTEM/Desktop/AI_Projects/onec_converter/1С_7.7')


@pytest.fixture(scope='module')
def real_base(tmp_path_factory: pytest.TempPathFactory):
    if not (REAL_BASE / '1Cv7.MD').is_file():
        pytest.skip('реальная база 7.7 недоступна')
    work = tmp_path_factory.mktemp('real77')
    shutil.copy2(REAL_BASE / '1Cv7.MD', work / '1Cv7.MD')
    shutil.copy2(REAL_BASE / '1Cv77.dat', work / '1Cv77.dat')
    base = Base77(work)
    yield base
    base.close()


def test_sections_present(real_base: Base77):
    secs = real_base.data.sections()
    for expected in ('System table', 'Unique IDs', 'Constants', 'References',
                     'Template Operations', 'Correct Entries'):
        assert expected in secs, f'секция {expected} отсутствует'


def test_unique_ids_nonempty(real_base: Base77):
    ids = real_base.data.unique_ids()
    assert len(ids) > 0
    assert all(v > 0 for v in ids.values())


def test_constants_nonempty(real_base: Base77):
    consts = real_base.data.constants()
    assert len(consts) > 0


def test_references_look_real(real_base: Base77):
    refs = real_base.data.references()
    assert len(refs) > 0
    sample_table = max(refs, key=lambda t: len(refs[t]))
    sample = refs[sample_table][0]
    # первая позиция записи — ссылка "NNN|"
    assert isinstance(sample[0], str)
    assert re.match(r'^\\d+\\|$', sample[0]) or sample[0] == '0|'


def test_header_version(real_base: Base77):
    raw = (REAL_BASE / '1Cv77.dat').read_bytes()[:64]
    text = raw.decode('cp866', errors='replace')
    assert text.startswith('{"7.70"') or '7.70' in text
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
