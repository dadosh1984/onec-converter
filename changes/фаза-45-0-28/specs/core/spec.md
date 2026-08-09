# Spec: core

## Purpose
Углубить AI-навыки (confidence в авто-маппинге, сохранение саммари),
выставить их в CLI (ai-map/ai-explain), добавить mint-token --dry-run/--json
и rate-limit в Module.bsl. Версия 0.28.0.

## Acceptance criteria
- [x] auto_map_schemas: каждое правило с confidence — 'exact' (по
      нормализованному имени) или 'synonym' (по синониму)
- [x] compress_metadata(meta, top_tables, out_path) пишет саммари JSON-файлом
- [x] CLI ai-map: правила TOON из read_metadata двух баз, --out или stdout
- [x] CLI ai-explain: explain_diff(diff_structures(...)) построчно
- [x] CLI mint-token: --dry-run (header/payload без подписи), --json
      ({"token","exp"})
- [x] Module.bsl::ПроверитьКлюч: Перем СчётчикНеудач; >=5 — отказ; сброс при
      успехе; честный комментарий (HTTP-сервис 1С: переменные модуля не
      гарантируют хранение между запросами — для production внешний
      rate-limiter)
- [x] Ворота: pytest (+6), conformance, ruff, mypy, check_bsl, vitest —
      зелёные; релиз 0.28.0
