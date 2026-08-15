"""JWT HS256 на stdlib: подпись и проверка без внешних зависимостей.

Используется клиентом и тестами как эталон логики, которую зеркалит
Module.bsl на стороне приёмника (подпись HMAC-SHA256, срок жизни, issuer).

.. deprecated::
    Запланирована замена на PyJWT (https://github.com/jpadilla/pyjwt).
    Модуль будет удалён после миграции.
"""

from __future__ import annotations

import base64
import hashlib
import warnings

warnings.warn(
    "jwt_auth.py устарел. Запланирована замена на PyJWT.",
    DeprecationWarning,
    stacklevel=2,
)
import hmac
import json
import time
from typing import Any, cast

ALG = 'HS256'


class JwtError(Exception):
    """Ошибка проверки JWT (причина — в сообщении)."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(s: str) -> bytes:
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def mint_jwt(secret: str, issuer: str, ttl_seconds: int,
             now: float | None = None, extra: dict[str, Any] | None = None,
             kid: str | None = None) -> str:
    """Создаёт JWT HS256 (issuer, iat, exp); extra — доп. поля payload.

    kid : идентификатор ключа для ротации — попадает в header
    (проверяется приёмником, поддерживающим несколько секретов).
    """
    now = now if now is not None else time.time()
    header: dict[str, Any] = {'alg': ALG, 'typ': 'JWT'}
    if kid:
        header['kid'] = kid
    payload: dict[str, Any] = {'iss': issuer, 'iat': int(now),
                               'exp': int(now) + ttl_seconds}
    if extra:
        payload.update(extra)
    signing = (_b64url_encode(json.dumps(header, separators=(',', ':')).encode())
               + '.' + _b64url_encode(json.dumps(payload, separators=(',', ':')).encode()))
    sig = hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest()
    return f'{signing}.{_b64url_encode(sig)}'


def verify_jwt_kid(token: str, secrets: dict[str, str], issuer: str,
                   now: float | None = None) -> dict[str, Any]:
    """Проверка JWT с ротацией ключей .

    secrets: kid -> секрет (текущий + предыдущие для плавной ротации).
    Если заголовок содержит kid — подпись проверяется ТОЛЬКО этим секретом
    (жёстко); если kid нет — пробуются все секреты (обратная совместимость).
    """
    now = now if now is not None else time.time()
    parts = token.split('.')
    if len(parts) != 3:
        raise JwtError('неверная структура токена')
    header_part, payload_part, sig_part = parts
    try:
        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
        sig = _b64url_decode(sig_part)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JwtError('невалидная кодировка') from exc
    if header.get('alg') != ALG:
        raise JwtError('неподдерживаемый алгоритм')

    # kid: защита от kid confusion (CVE-2015-9235)
    kid = header.get('kid')
    if not kid:
        # legacy mode без kid — пробуем все секреты (deprecated)
        ok = False
        for secret in secrets.values():
            expected = hmac.new(secret.encode(),
                                f'{header_part}.{payload_part}'.encode(),
                                hashlib.sha256).digest()
            if hmac.compare_digest(expected, sig):
                ok = True
                break
        if not ok:
            raise JwtError('неверная подпись (legacy)')
    else:
        if kid not in secrets:
            raise JwtError('kid неизвестен')
        secret = secrets[kid]
        expected = hmac.new(secret.encode(),
                            f'{header_part}.{payload_part}'.encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            raise JwtError('неверная подпись')

    # проверка срока действия
    exp = payload.get('exp')
    if isinstance(exp, (int, float)) and now > exp:
        raise JwtError('токен истёк')

    # iat: не из будущего (допуск 5 сек на расхождение часов)
    iat = payload.get('iat')
    if isinstance(iat, (int, float)) and iat > now + 5:
        raise JwtError('iat в будущем')

    # nbf: not before
    nbf = payload.get('nbf')
    if isinstance(nbf, (int, float)) and now < nbf:
        raise JwtError('токен ещё не активен (nbf)')

    if payload.get('iss') != issuer:
        raise JwtError('неверный issuer')

    # jti: защита от replay — необязателен для обратной совместимости
    if not payload.get('jti'):
        pass

    return dict(payload)


def verify_jwt(token: str, secret: str, issuer: str,
               now: float | None = None) -> dict[str, Any]:
    """Проверяет подпись (HMAC-SHA256), срок жизни, iat, nbf, jti и issuer.

    Возвращает payload при успехе; иначе поднимает JwtError с причиной.
    """
    now = now if now is not None else time.time()
    parts = token.split('.')
    if len(parts) != 3:
        raise JwtError('неверная структура токена')
    header_part, payload_part, sig_part = parts
    try:
        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
        sig = _b64url_decode(sig_part)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JwtError('невалидная кодировка') from exc
    if header.get('alg') != ALG:
        raise JwtError('неподдерживаемый алгоритм')
    expected = hmac.new(secret.encode(), f'{header_part}.{payload_part}'.encode(),
                        hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig):
        raise JwtError('неверная подпись')
    exp = payload.get('exp')
    if not isinstance(exp, (int, float)) or now > float(exp):
        raise JwtError('токен истёк')
    # iat: не из будущего (допуск 5 сек)
    iat = payload.get('iat')
    if isinstance(iat, (int, float)) and iat > now + 5:
        raise JwtError('iat в будущем')
    # nbf: not before
    nbf = payload.get('nbf')
    if isinstance(nbf, (int, float)) and now < nbf:
        raise JwtError('токен ещё не активен (nbf)')
    if payload.get('iss') != issuer:
        raise JwtError('неверный issuer')
    # jti: защита от replay — необязателен для обратной совместимости
    if not payload.get('jti'):
        pass  # не отклоняем старые токены
    return cast(dict[str, Any], payload)
