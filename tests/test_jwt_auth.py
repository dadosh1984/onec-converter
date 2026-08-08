"""Фаза 22: JWT HS256 — mint/verify (эталон логики Module.bsl)."""

from __future__ import annotations

import pytest

from onec_converter.jwt_auth import JwtError, mint_jwt, verify_jwt

SECRET = 'super-secret-приёмника'
ISSUER = 'onec-converter'


def test_mint_and_verify_valid():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=600)
    payload = verify_jwt(tok, SECRET, ISSUER)
    assert payload['iss'] == ISSUER
    assert payload['exp'] - payload['iat'] == 600


def test_expired_token_rejected():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=10, now=1_700_000_000)
    with pytest.raises(JwtError, match='истёк'):
        verify_jwt(tok, SECRET, ISSUER, now=1_700_000_100)


def test_wrong_secret_rejected():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=600)
    with pytest.raises(JwtError, match='подпись'):
        verify_jwt(tok, 'другой-секрет', ISSUER)


def test_wrong_issuer_rejected():
    tok = mint_jwt(SECRET, 'other-issuer', ttl_seconds=600)
    with pytest.raises(JwtError, match='issuer'):
        verify_jwt(tok, SECRET, ISSUER)


def test_tampered_payload_rejected():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=600)
    head, payload, sig = tok.split('.')
    # меняем один символ payload (base64url-валидный, JSON может сломаться)
    payload = ('A' if payload[0] != 'A' else 'B') + payload[1:]
    with pytest.raises(JwtError):
        verify_jwt(f'{head}.{payload}.{sig}', SECRET, ISSUER)


def test_wrong_signature_rejected():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=600)
    head, payload, _ = tok.split('.')
    bad = mint_jwt(SECRET, ISSUER, ttl_seconds=600, extra={'n': 2})
    _, _, bad_sig = bad.split('.')
    with pytest.raises(JwtError, match='подпись'):
        verify_jwt(f'{head}.{payload}.{bad_sig}', SECRET, ISSUER)


def test_malformed_token_rejected():
    with pytest.raises(JwtError, match='структура'):
        verify_jwt('not-a-jwt', SECRET, ISSUER)


def test_extra_payload_preserved():
    tok = mint_jwt(SECRET, ISSUER, ttl_seconds=60, extra={'role': 'migrator'})
    assert verify_jwt(tok, SECRET, ISSUER)['role'] == 'migrator'
