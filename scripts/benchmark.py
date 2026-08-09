"""Бенчмарк производительности парсинга (Фаза 38, nightly-bench).

Строит fake-базу, замеряет: время чтения метаданных, полного чтения строк,
extract-а; выдаёт метрики (timeit-цикл) для CI-сравнения между коммитами.
Код авторский.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from onec_converter.fake_1cd import FixtureField, FixtureTable, build_fake_1cd, encode_row


def _build_fake(path: Path, tables: int = 20, rows_per_table: int = 5000) -> None:
    F = [FixtureField('_VERSION', 'RV', length=2),
         FixtureField('_IDRREF', 'B', length=16),
         FixtureField('_CODE', 'NC', length=9),
         FixtureField('_DESCRIPTION', 'NVC', length=40)]
    def mk(i: int) -> FixtureTable:
        return FixtureTable(f'_Reference{i}', fields=F, rows=[
            encode_row(F, {'_IDRREF': b'\x01' * 16, '_CODE': f'{r:05d}',
                           '_DESCRIPTION': f'item {r}'})
            for r in range(rows_per_table)])
    path.write_bytes(build_fake_1cd([mk(i) for i in range(tables)]))


def bench(path: Path, iterations: int = 3) -> dict[str, float]:
    """Замерить время чтения метаданных и полного обхода строк."""
    from onec_converter.source_8x_file import Database1CD, read_table

    t_meta = 0.0
    t_full = 0.0
    rows = 0
    for _ in range(iterations):
        with Database1CD(path) as db:
            s = time.perf_counter()
            _ = sorted(db.tables)
            t_meta += time.perf_counter() - s

            s = time.perf_counter()
            n = sum(1 for tn in sorted(db.tables) for _ in read_table(path, tn))
            t_full += time.perf_counter() - s
            rows = n
    return {
        'metadata_ms': round(t_meta / iterations * 1000, 2),
        'read_all_ms': round(t_full / iterations * 1000, 2),
        'rows': float(rows),
        'rows_per_sec': round(rows / (t_full / iterations), 0),
    }


def main() -> int:
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/onec_bench')
    work.mkdir(parents=True, exist_ok=True)
    cd = work / 'bench.1CD'
    _build_fake(cd)
    res = bench(cd)
    print('onec_benchmark metadata_ms=%.2f read_all_ms=%.2f rows=%.0f rows_per_sec=%.0f'
          % (res['metadata_ms'], res['read_all_ms'], res['rows'],
             res['rows_per_sec']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
