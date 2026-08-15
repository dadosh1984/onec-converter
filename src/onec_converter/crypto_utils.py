"""Общие криптопримитивы (sha256 / hmac)

Единый источник для hashlib-обёрток, ранее дублированных в audit.py,
s3_client.py и anonymizer.py. Хеши SHA-256 без соли — для аудита целостности
и подписей запросов S3 (не пароли).
"""
from __future__ import annotations

import hashlib
import hmac


def sha256_hex(data: str | bytes) -> str:
    """SHA-256 hexdigest от строки (utf-8) или байтов."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def hmac_sha256(key: bytes, msg: str | bytes) -> bytes:
    """HMAC-SHA256 (raw bytes) от сообщения строкой/байтами."""
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).digest()


def hmac_sha256_hex(key: bytes, msg: str | bytes) -> str:
    """HMAC-SHA256 hexdigest."""
    return hmac_sha256(key, msg).hex()
