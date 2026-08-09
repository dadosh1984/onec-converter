# Tasks — Фаза 49: память и потоковость (0.32.0)

## Потоковость
- [x] [fact] v77_reader потоково: mmap-сканер секций (U35/U4)
- [x] [fact] s3 upload_file стримингом, dump-report на нём (U36/U5)
- [x] [fact] table_stats_all одним проходом (U37)
- [x] [fact] guid_diff: проверен — нет-оп (U38)
- [x] [fact] read_metadata in-memory LRU (U39)
- [x] [fact] dump-records потоковый JSON/CSV + --max-bytes (U40)
- [x] [fact] cache.put атомарно tmp+rename (U42)

## Качество
- [x] [fact] fix ruff F841 (db_ctx); тесты +11 (test_phase49_memory.py)

## Релиз
- [x] [assumption] ворота зелёные; релиз 0.32.0
