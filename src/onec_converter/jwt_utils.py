"""JWT на PyJWT — замена самописного jwt_auth.py."""

from __future__ import annotations

from typing import Any

import jwt

from .errors import SecurityError

_ALGORITHMS = ["HS256"]


def encode_jwt(
    payload: dict[str, Any],
    secret: str,
    kid: str,
    expires_in: int = 3600,
) -> str:
    """Создать JWT HS256 через PyJWT.

    payload: произвольные claims.
    secret: shared secret (HMAC ключ).
    kid: идентификатор ключа (попадает в header).
    expires_in: TTL в секундах.
    """
    claims = dict(payload)
    headers = {"kid": kid}
    # PyJWT автоматически добавляет exp, но не iat/jti
    import time, uuid
    now = int(time.time())
    if "iat" not in claims:
        claims["iat"] = now
    if "exp" not in claims:
        claims["exp"] = now + expires_in
    if "jti" not in claims:
        claims["jti"] = str(uuid.uuid4())[:16]
    return jwt.encode(claims, secret, algorithm="HS256", headers=headers)


def verify_jwt(
    token: str,
    secrets: dict[str, str],
) -> dict[str, Any]:
    """Верифицировать JWT HS256 через PyJWT.

    secrets: {kid: secret} — по kid из header выбирается секрет.
    Проверяется: подпись, exp, iat (не из будущего), nbf.
    """
    from jwt import get_unverified_header
    try:
        header = get_unverified_header(token)
        kid = header.get("kid")
        if not kid or kid not in secrets:
            raise SecurityError(f"kid {kid!r} отсутствует или неизвестен")

        decoded = jwt.decode(
            token,
            secrets[kid],
            algorithms=_ALGORITHMS,
            options={
                "require": ["iss", "iat", "jti"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
            },
        )
    except jwt.ExpiredSignatureError as e:
        raise SecurityError("Токен истёк") from e
    except jwt.InvalidTokenError as e:
        raise SecurityError(f"Неверная подпись или claims: {e}") from e

    return decoded
