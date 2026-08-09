# Spec: core

## Purpose
Закрыть секреты (пароли/токены/ключи) от утечки в журналы/исключения,
дать ротацию JWT-ключей, идемпотентность и лимиты приёма пакетов 1С,
секрет-сканер коммитов и надёжные уведомления. Версия 0.35.0.

## Acceptance criteria
- [x] mask_secrets: userinfo (user:**:@host) и key=token/password/
      client_secret/secret; применён в sql_source исключениях (U8/U27)
- [x] s3 assume_role (STS Signed POST) возвращает temporary credentials (U28)
- [x] BSL: лимит пакета (413, max 1000) + идемпотентность в пакете по `idem`
      (U29/U32); client идемпотентность сетевых ретраев — replace=true
- [x] JWT kid/ротация: mint_jwt(kid), verify_jwt_kid, CLI mint-token --kid,
      BSL ПроверитьJWT по НаборСекретовJWT (U30)
- [x] .githooks/pre-commit секрет-сканер (AKIA/ASIА/private key/password/
      client_secret в диффе блокируют) (U31)
- [x] notify ретраит 5xx + сеть, 4xx — нет (U33)
- [x] ruff/mypy/pytest/check_bsl зелёные; релиз 0.35.0
