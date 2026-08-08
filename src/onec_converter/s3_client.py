"""Минимальный S3-клиент для экспорта отчётов (Фаза 27, идея 1c-s3connector).

Авторская реализация AWS SigV4 (PUT object) на stdlib — без boto3:
`put_object` загружает файл в bucket по path-style URL
(`https://<endpoint>/<bucket>/<key>`); кастомный endpoint позволяет
использовать S3-совместимые хранилища (MinIO, Yandex Object Storage и т.п.).

Подпись SigV4: canonical request (method/path/query/headers/signed headers/
payload hash) + string-to-sign (AWS4-HMAC-SHA256, дата, scope) + HMAC-цепочка
на секретном ключе. Проверено юнит-тестом на каноническом AWS-примере.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import os
import urllib.request
from typing import Any

_ISO = '%Y%m%dT%H%M%SZ'
_DAY = '%Y%m%d'


class S3Error(Exception):
    """Ошибка экспорта в S3."""


def _hmac(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_v4(access_key: str, secret_key: str, *, method: str, path: str,
            host: str, payload: bytes, region: str = 'us-east-1',
            service: str = 's3', now: datetime.datetime | None = None,
            query: str = '') -> tuple[str, str, str]:
    """Канонический AWS SigV4: возвращает (authorization, amz_date, sha256).

    path — URL-путь объекта (например `/bucket/key`); host — заголовок Host
    (без порта); query — необязательная строка запроса.
    """
    dt = now or datetime.datetime.now(datetime.UTC)
    amz_date = dt.strftime(_ISO)
    day = dt.strftime(_DAY)
    payload_hash = _sha256_hex(payload)

    canonical_headers = (
        f'host:{host}\n'
        f'x-amz-content-sha256:{payload_hash}\n'
        f'x-amz-date:{amz_date}\n')
    signed_headers = 'host;x-amz-content-sha256;x-amz-date'
    canonical_request = (
        f'{method}\n{path}\n{query}\n'
        f'{canonical_headers}\n{signed_headers}\n{payload_hash}')

    scope = f'{day}/{region}/{service}/aws4_request'
    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256', amz_date, scope, _sha256_hex(
            canonical_request.encode())])

    k_date = _hmac(('AWS4' + secret_key).encode(), day.encode())
    k_region = _hmac(k_date, region.encode())
    k_service = _hmac(k_region, service.encode())
    k_signing = _hmac(k_service, b'aws4_request')
    signature = hmac.new(k_signing, string_to_sign.encode(),
                         hashlib.sha256).hexdigest()

    authorization = (
        f'AWS4-HMAC-SHA256 Credential={access_key}/{scope}, '
        f'SignedHeaders={signed_headers}, Signature={signature}')
    return authorization, amz_date, payload_hash


def _endpoint_url(endpoint: str, bucket: str, key: str) -> tuple[str, str]:
    """(url, host): по умолчанию virtual-hosted AWS; иначе path-style."""
    if endpoint:
        ep = endpoint.rstrip('/')
        return f'{ep}/{bucket}/{key}', ep.split('://', 1)[-1].split('/', 1)[0]
    host = f'{bucket}.s3.amazonaws.com'
    return f'https://{host}/{key}', host


def put_object(bucket: str, key: str, data: bytes, *,
               access_key: str = '', secret_key: str = '',
               endpoint: str = '', region: str = 'us-east-1',
               content_type: str = 'application/json',
               timeout: int = 60) -> dict[str, Any]:
    """Загрузить объект в S3 (PUT). Ключи — из аргументов или env
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY. Возвращает {ok, url, key}."""
    ak = access_key or os.environ.get('AWS_ACCESS_KEY_ID', '')
    sk = secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    if not ak or not sk:
        raise S3Error('нет ключей: передайте --key/--secret или AWS_*')

    url, host = _endpoint_url(endpoint, bucket, key)
    path = '/' + '/'.join(part for part in url.split('://', 1)[1].split(
        '/', 1)[1:]) if endpoint else '/' + key
    authorization, amz_date, payload_hash = sign_v4(
        ak, sk, method='PUT', path=path, host=host, payload=data,
        region=region)

    req = urllib.request.Request(
        url, data=data, method='PUT',
        headers={
            'Host': host,
            'Content-Type': content_type,
            'Content-Length': str(len(data)),
            'x-amz-content-sha256': payload_hash,
            'x-amz-date': amz_date,
            'Authorization': authorization,
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {'ok': True, 'url': url, 'key': key,
                    'status': resp.status}
    except urllib.error.URLError as exc:
        raise S3Error(f'S3 PUT не удался: {exc}') from exc
