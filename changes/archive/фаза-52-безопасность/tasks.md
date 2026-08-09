# Tasks — Фаза 52: Безопасность (0.35.0)

## Секреты
- [x] [fact] mask_secrets для DSN/URL, применён в sql_source (U8/U27)
- [x] [fact] s3 assume_role STS (U28)
- [x] [fact] pre-commit секрет-сканер (U31)

## Приёмник/клиент
- [x] [fact] BSL лимит пакета 413/1000 + idem (U29/U32)
- [x] [fact] JWT kid/ротация (U30)
- [x] [fact] notify ретрай 5xx (U33)

## Релиз
- [x] [assumption] ворота зелёные; релиз 0.35.0
