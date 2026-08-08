"""Тесты CLI load: файл-приёмник и HTTP-загрузка (Фаза 9)."""
from __future__ import annotations

import json
from pathlib import Path

from onec_converter.cli import main
from onec_converter.intermediate import make_object


def _batch(tmp_path: Path) -> Path:
    objs = [
        make_object('Справочник.Банки', '1|', ['0001', 'Банк А'],
                    {'Код': '0001', 'Наименование': 'Банк А'}, {}),
        make_object('Справочник.Банки', '2|', ['0002', 'Банк Б'],
                    {'Код': '0002', 'Наименование': 'Банк Б'}, {}),
    ]
    f = tmp_path / 'batch.json'
    f.write_text(json.dumps(objs, ensure_ascii=False), encoding='utf-8')
    return f


def _result(created: int, errors: list[str]) -> object:
    return type('LR', (), {'created': created, 'updated': 0, 'errors': errors})()


def test_load_file_target(tmp_path: Path):
    """file-режим: --target каталог → туда пишется load.json."""
    batch = _batch(tmp_path)
    target = tmp_path / 'receiver'
    target.mkdir()
    rc = main(['load', '--input', str(batch), '--target', str(target)])
    assert rc == 0
    out = target / 'load.json'
    assert out.is_file()
    assert len(json.loads(out.read_text(encoding='utf-8'))) == 2


def test_load_file_path(tmp_path: Path):
    """file-режим: --target путь к файлу → запись в него."""
    batch = _batch(tmp_path)
    target = tmp_path / 'out' / 'data.json'
    rc = main(['load', '--input', str(batch), '--target', str(target)])
    assert rc == 0
    assert target.is_file()


def test_load_http_ok(tmp_path: Path, monkeypatch, capsys):
    """HTTP-режим: успешная загрузка (mock клиента, без ретраев)."""
    batch = _batch(tmp_path)

    class FakeHttp:
        def __init__(self, base_url: str, retries: int = 3,
                     api_key: str | None = None,
                     token_url: str | None = None,
                     client_id: str | None = None,
                     client_secret: str | None = None):
            self.base_url = base_url

        async def load(self, objects, source_ib, target_ib, replace=False):
            assert source_ib == 'srcA' and target_ib == 'tgtX'
            return [_result(len(objects), [])]

        async def aclose(self):
            pass

    import onec_converter.cli as cli_mod
    monkeypatch.setattr(cli_mod, 'HttpClient83', FakeHttp)
    rc = main(['load', '--input', str(batch), '--http', 'http://x',
               '--source-ib', 'srcA', '--target-ib', 'tgtX'])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out['ok'] is True
    assert out['created'] == 2


def test_load_http_errors(tmp_path: Path, monkeypatch, capsys):
    """HTTP-режим: ошибки сервиса → exit 1 и отчёт об ошибках."""
    batch = _batch(tmp_path)

    class FakeHttp:
        def __init__(self, base_url: str, retries: int = 3,
                     api_key: str | None = None,
                     token_url: str | None = None,
                     client_id: str | None = None,
                     client_secret: str | None = None):
            self.base_url = base_url

        async def load(self, objects, source_ib, target_ib, replace=False):
            return [_result(0, ['дубликат ключа: 0001'])]

        async def aclose(self):
            pass

    import onec_converter.cli as cli_mod
    monkeypatch.setattr(cli_mod, 'HttpClient83', FakeHttp)
    rc = main(['load', '--input', str(batch), '--http', 'http://x'])
    assert rc == 1
    err = capsys.readouterr().err
    assert 'ошибки загрузки' in err
    assert 'дубликат ключа' in err
