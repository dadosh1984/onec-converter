"""Тесты PyJWT — encode/verify, exp, kid."""

from __future__ import annotations

import pytest

from onec_converter.errors import SecurityError
from onec_converter.jwt_utils import encode_jwt, verify_jwt

_SECRETS = {"key1": "supersecret", "key2": "othersecret"}


def test_roundtrip():
    token = encode_jwt({"sub": "user", "iss": "test"}, "supersecret", "key1")
    decoded = verify_jwt(token, _SECRETS)
    assert decoded["sub"] == "user"
    assert decoded["iss"] == "test"


def test_wrong_secret():
    token = encode_jwt({"sub": "user", "iss": "test"}, "wrongsecret", "key1")
    with pytest.raises(SecurityError):
        verify_jwt(token, _SECRETS)


def test_missing_kid():
    # PyJWT.encode без kid в заголовке
    import jwt
    token = jwt.encode({"sub": "user"}, "secret", algorithm="HS256")
    with pytest.raises(SecurityError, match="kid"):
        verify_jwt(token, {"key1": "secret"})


def test_unknown_kid():
    token = encode_jwt({"sub": "user", "iss": "test"}, "secret", "unknown_kid")
    with pytest.raises(SecurityError, match="kid"):
        verify_jwt(token, _SECRETS)


def test_iss_required():
    token = encode_jwt({"sub": "user"}, "supersecret", "key1")
    with pytest.raises(SecurityError):
        verify_jwt(token, _SECRETS)
