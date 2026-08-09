# Spec: core

## Purpose
Укрепить tamper-evident аудит до комплаенс-уровня: сквозная проверка
цепочки через архивы ротации, кеш хвоста файла, маскирование ПДн по
умолчанию (opt-out), единые криптопримитивы. Версия 0.25.0.

## Acceptance criteria
- [x] verify_audit(cross_files=True): при наличии audit.jsonl.1/.2/...
      prev_hash первой записи каждого следующего файла обязан равняться
      хешу последней записи предыдущего; нарушение -> 'граница файла'
- [x] _last_record_hash: кеш (путь, mtime_ns, size); повторное открытие
      того же файла не перечитывает его (тест со spy на open)
- [x] AuditLog/set_audit: pii_masking=True по умолчанию; отключение —
      явный pii_masking=False / CLI --no-pii-masking (флаг инвертирован)
- [x] crypto_utils.py: sha256_hex/hmac_sha256/hmac_sha256_hex; audit,
      s3_client, anonymizer используют его (дубли удалены)
- [x] Мутационный fuzz: каждая посимвольная мутация каждой записи
      детектируется verify_audit (детерминированный прогон)
- [x] CLI audit-verify --audit-file [--cross-files]: rc 0/1; реестр CLI 24
- [x] Формула hash/prev_hash (sort_keys, без 'hash', ensure_ascii=False)
      задокументирована в audit.py
- [x] Ворота: pytest (+9), conformance, ruff, mypy (52), check_bsl,
      vitest — зелёные; релиз 0.25.0
