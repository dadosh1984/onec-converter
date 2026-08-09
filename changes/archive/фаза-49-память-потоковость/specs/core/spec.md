# Spec: core

## Purpose
Снизить пиковую память при работе с большими файлами: v77 (1Cv77.dat),
S3-загрузка отчётов, статистика таблиц, метаданные MCP-сессий, вывод
dump-records, атомарность кеша. Версия 0.32.0.

## Acceptance criteria
- [x] V77Reader читает секции через mmap-сканер (iter_sections_text):
      одна секция в памяти, а не весь файл; API sections()/unique_ids()/
      constants()/references() не меняется; from_bytes остаётся
- [x] s3.upload_file(bucket, key, path, ...): sha256+размер первым
      проходом, тело чанками через http.client; O(1) память;
      cmd_dump_report использует upload_file вместо f.read_bytes()
- [x] Database1CD.table_stats_all(): статистика всех таблиц одним
      проходом, общий кеш
- [x] read_metadata: in-memory LRU (8) поверх дискового кеша; ключ —
      file_key (mtime+size+голова), устаревание исключено
- [x] dump-records: потоковый JSON-массив/CSV в stdout + --max-bytes;
      stdout остаётся машиночитаемым
- [x] Cache.put: tmp+os.replace — битый артефакт невозможен
- [x] ruff/mypy/pytest зелёные; релиз 0.32.0
