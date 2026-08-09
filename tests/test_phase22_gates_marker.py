"""Фаза 22: статические ворота — JWT-проверка в Module.bsl и [auth] в конфиге."""

from __future__ import annotations

from pathlib import Path

from onec_converter.config import ProjectConfig

BSL = Path(__file__).resolve().parents[1] / 'src/onec_converter/extension_83/Module.bsl'


def test_bsl_has_jwt_verification():
    text = BSL.read_text(encoding='utf-8-sig')
    for needle in ['ПроверитьТокен', 'ПроверитьJWT', 'HMACSHA256',
                   'ОжидаемыйIssuer', 'ПобитовыйИсключительноеИЛИ',
                   '"authorization"', '"bearer"']:
        assert needle in text, f'Module.bsl: отсутствует {needle}'


def test_bsl_accepts_key_or_token():
    text = BSL.read_text(encoding='utf-8-sig')
    # shared-secret остаётся, JWT — дополнение, а не замена
    assert 'x-api-key' in text
    assert 'ПроверитьТокен(Запрос)' in text
    assert 'СчётчикНеудач' in text  # rate-limit (Фаза 45)


def test_config_auth_section(tmp_path: Path):
    cfg = tmp_path / 'onec.toml'
    cfg.write_text(
        '[auth]\n'
        'token_url = "http://srv/token"\n'
        'client_id = "cid"\n'
        'client_secret = "csecret"\n',
        encoding='utf-8')
    c = ProjectConfig.load(cfg)
    assert c.token_url == 'http://srv/token'
    assert c.client_id == 'cid'
    assert c.client_secret == 'csecret'
