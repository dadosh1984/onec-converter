# Spec: core

## Purpose
Фаза 31 — качество и DX: TTL/лимит кеша (LRU), fuzz-тест anonymizer,
нормализация в replace Module.bsl, документация аутентификации.

## Requirements
- [REQ-1] Cache.trim(max_bytes, ttl_seconds) — эвикция; stats c возрастом.
- [REQ-2] fuzz-тест anonymizer (свой генератор, без hypothesis): случайные и
  обычные строки не портятся.
- [REQ-3] Module.bsl: СокрЛП перед поиском в replace.
- [REQ-4] Доки: аутентификация (X-API-Key/--api-key), CHANGELOG 0.4.0.
- [REQ-5] Ворота зелёные; релиз 0.4.0.
