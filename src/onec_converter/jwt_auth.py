"""JWT HS256 на stdlib (Фаза 22): подпись и проверка без внешних зависимостей.

Используется клиентом и тестами как эталон логики, которую зеркалит
Module.bsl на стороне приёмника (подпись HMAC-SHA256, срок жизни, issuer).
"""

from __future__ import annotations

import base64
import hashlib
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
             now: float | None = None, extra: dict[str, Any] | None = None) -> str:
    """Создаёт JWT HS256 (issuer, iat, exp); extra — доп. поля payload."""
    now = now if now is not None else time.time()
    header = {'alg': ALG, 'typ': 'JWT'}
    payload: dict[str, Any] = {'iss': issuer, 'iat': int(now),
                               'exp': int(now) + ttl_seconds}
    if extra:
        payload.update(extra)
    signing = (_b64url_encode(json.dumps(header, separators=(',', ':')).encode())
               + '.' + _b64url_encode(json.dumps(payload, separators=(',', ':')).encode()))
    sig = hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest()
    return f'{signing}.{_b64url_encode(sig)}'


def verify_jwt(token: str, secret: str, issuer: str,
               now: float | None = None) -> dict[str, Any]:
    """Проверяет подпись (HMAC-SHA256), срок жизни и issuer.

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
    if payload.get('iss') != issuer:
        raise JwtError('неверный issuer')
    return cast(dict[str, Any], payload)
