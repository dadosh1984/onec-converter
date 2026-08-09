"""Тесты версии релиза MCP-сервера и уведомления об обновлении (0.43.0).

- serverInfo.version == onec_converter.__version__ (виден любому MCP-клиенту
  по стандарту).
- баннер версии + обновления в stderr (человекочитаемый, utf-8).
- _server_meta() встраивает server_version (и, при наличии обновления, update)
  в тело ответа тула — доходит до ЛЮБОГО агента через результат тула.
- проверка PyPI: таймаут + дисковый кеш на сутки (не «стучим» в сеть
  при каждом lazy-старте).
"""
from __future__ import annotations

from onec_converter import __version__


# ---- serverInfo.version == наш релиз ----
def test_serverinfo_version_matches(monkeypatch):
    from onec_converter import mcp_server

    server = getattr(mcp_server, 'mcp', None)
    assert server is not None
    vsrv = getattr(server, '_mcp_server', None)
    # наш код выставляет version на _mcp_server при импорте модуля
    if vsrv is not None:
        assert vsrv.version == __version__


# ---- баннер версии в stderr (utf-8, человек-читаемо) ----
def test_banner_prints_release(tmp_path, capsys, monkeypatch):
    from onec_converter import version_check as vc

    monkeypatch.setattr(vc, 'latest_version', lambda: __version__)
    vc._VERSION_CACHE = tmp_path / 'vc'  # изолируем кеш
    vc.print_version_to_stderr(skip_update_check=False, _now='09:00:00')
    err = capsys.readouterr().err
    assert __version__ in err
    assert 'релиз' in err


# ---- уведомление об обновлении при наличии новой версии ----
def test_banner_reports_update(tmp_path, capsys, monkeypatch):
    from onec_converter import version_check as vc

    monkeypatch.setattr(vc, 'latest_version', lambda: '99.99.99')
    vc._VERSION_CACHE = tmp_path / 'vc'
    vc.print_version_to_stderr(skip_update_check=False, _now='09:00:01')
    err = capsys.readouterr().err
    assert 'новую версию' in err.lower() or 'Доступна' in err or '99.99.99' in err


# ---- ONEC_NO_UPDATE_CHECK отключает проверку ----
def test_banner_respects_no_update_check(capsys, monkeypatch):
    from onec_converter import version_check as vc

    monkeypatch.setenv('ONEC_NO_UPDATE_CHECK', '1')
    vc.print_version_to_stderr(skip_update_check=None, _now='09:00:02')
    err = capsys.readouterr().err
    assert 'проверка обновления отключена' in err
    assert '99.' not in err


# ---- дисковый кеш: повторная проверка не стучит в сеть ----
def test_latest_version_cached(monkeypatch, tmp_path):
    from onec_converter import version_check as vc

    calls = []

    def fake_fetch(timeout=0.0):
        calls.append(timeout)
        return '9.9.9'

    monkeypatch.setattr(vc, '_VERSION_CACHE', tmp_path / 'vc.json')
    monkeypatch.setattr(vc, '_fetch_latest', fake_fetch)
    assert vc.latest_version() == '9.9.9'
    assert vc.latest_version() == '9.9.9'  # второй раз — из кеша
    assert len(calls) == 1, 'второй вызов должен быть из кеша, не из сети'


# ---- _server_meta встраивает server_version и update ----
def test_server_meta_injects_version_and_update(monkeypatch):
    from onec_converter import mcp_server

    mcp_server._SERVER_META_CACHE = None
    monkeypatch.setattr(mcp_server, '_latest_network', lambda: None)
    meta = mcp_server._server_meta()
    assert meta['server_version'] == __version__
    assert 'update' not in meta

    # при наличии новой версии -> update в мете (не зависит от сети)
    mcp_server._SERVER_META_CACHE = None
    monkeypatch.setattr(mcp_server, '_latest_local_cache', lambda: '99.99.99')
    meta2 = mcp_server._server_meta()
    assert meta2['server_version'] == __version__
    assert meta2['update']['available'] is True
    assert meta2['update']['latest'] == '99.99.99'
    assert 'pip install --upgrade' in meta2['update']['message']
