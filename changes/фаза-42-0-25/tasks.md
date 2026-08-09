# Tasks — Фаза 42: укрепление аудита/комплаенс (0.25.0)

## verify_audit
- [x] [fact] verify_audit(cross_files=True): границы с архивами .1/.2/...
- [x] [fact] _last_record_hash: кеш по (путь, mtime, size)

## Приватность
- [x] [fact] pii_masking=True по умолчанию (opt-out) + changelog-запись

## Инфраструктура
- [x] [fact] crypto_utils.py: общий sha256/hmac (audit, s3_client, anonymizer)
- [x] [fact] мутационный fuzz verify_audit (любая мутация байта детектируется)

## CLI/доки/релиз
- [x] [fact] CLI audit-verify --audit-file [--cross-files]; формула hash/prev_hash
- [x] [assumption] ворота зелёные; релиз 0.25.0
