#!/usr/bin/env python3
"""Лёгкая статическая проверка .bsl-файлов расширения 1С (без зависимостей).

Цель — поймать регрессии, которые 1С отвергнет при компиляции (см. баг:
дубль `Функция НайтиОбъект2` вместо обработчика). Проверяет:
  1) дубликаты имён Функция/Процедура в одном модуле (переопределение метода);
  2) обработчики HTTP (`ЗаписьДанных`, `МетаданныеИБ`) объявлены как `Экспорт`;
  3) для функций с параметрами — имя параметра не дублируется.

Авторский код. Использование: python scripts/check_bsl.py [путь.bsl ...]
exit 0 при чисто, ненулевой — при проблемах.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_FN_RE = re.compile(r'^\s*(Функция|Процедура)\s+([A-Za-zА-Яа-яЁё0-9_]+)\s*\(')
_EXP_FN_RE = re.compile(r'^\s*Функция\s+([A-Za-zА-Яа-яЁё0-9_]+)\s*\(')
_EXP_REQF = {'ЗаписьДанных', 'МетаданныеИБ'}
_PARAM_DUP = re.compile(r'^\s*Функция.*\(([^)]*)\)')



def check_bsl(path: Path) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding='utf-8-sig')
    names: dict[str, int] = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = _FN_RE.match(line)
        if not m:
            continue
        name, kind = m.group(2), m.group(1)
        if name in names:
            problems.append(f'{path.name}:{i} дубликат {kind} "{name}" '
                            f'(уже объявлена в строке {names[name]})')
        else:
            names[name] = i
        # дубли параметров
        pm = _PARAM_DUP.match(line)
        if pm:
            inner = pm.group(1).strip().rstrip(')')
            if inner:
                params = [p.strip().split()[0] for p in inner.split(',') if p.strip()]
                dups = {p for p in params if params.count(p) > 1}
                for d in dups:
                    problems.append(f'{path.name}:{i} дубликат параметра "{d}"')
        # обработчики HTTP должны быть Экспорт
        if kind == 'Функция' and name in _EXP_REQF and not line.rstrip().endswith('Экспорт'):
            problems.append(f'{path.name}:{i} обработчик "{name}" не объявлен Экспорт')
    return problems


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    targets = [Path(a) for a in args] if args else list(Path('src').rglob('*.bsl'))
    if not targets:
        targets = list(Path('src/onec_converter/extension_83').glob('*.bsl'))
    errors: list[str] = []
    seen = set()
    for p in targets:
        if p.is_file() and p.suffix == '.bsl' and str(p) not in seen:
            seen.add(str(p))
            errors.extend(check_bsl(p))
    if errors:
        print('\n'.join(errors))
        print(f'check_bsl: {len(errors)} проблема(ы)')
        return 1
    print(f'check_bsl: {len(seen)} файл(ов) — ок')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
