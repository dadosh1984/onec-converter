"""Версия MCP-сервера и уведомление об обновлении.

При старте сервера печатаем в **stderr** (stdout занят JSON-RPC) версию
релиза onec-converter. Если на PyPI вышла более свежая версия — уведомляем
(без блокировки старта и без сетевых запросов при каждом соединении).

Сетевую проверку делаем с коротким таймаутом и кешем на диске (.onec_cache/
version-check.json), чтобы многократный lazy-старт stdio-подпроцесса (как в
pi-mcp-extension) не стучал в PyPI каждый раз.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from . import __version__

PYPI_JSON = 'https://pypi.org/pypi/onec-converter/json'
_VERSION_CACHE = Path('.onec_cache') / 'version-check.json'
# проверяем сеть не чаще одного раза в сутки
_REFRESH_SECONDS = 24 * 3600


def current_version() -> str:
    """Версия установленного MCP-сервера."""
    return __version__


def _semver_tuple(v: str) -> tuple[int, int, int]:
    """(major, minor, patch) для семантического сравнения; невалидное -> (0,0,0)."""
    nums: list[int] = []
    for part in str(v).lstrip('v').split('.'):
        digits = ''.join(ch for ch in part if ch.isdigit())
        try:
            nums.append(int(digits) if digits else 0)
        except ValueError:
            nums.append(0)
        if len(nums) >= 3:
            break
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _is_newer(latest: str | None, current: str) -> bool:
    """True, если latest строго новее current (по semver). Dev/editable-версия
    (local > PyPI) не считается обновлением."""
    if not latest:
        return False
    return _semver_tuple(latest) > _semver_tuple(current)


def _saved_check() -> dict[str, object] | None:
    try:
        data = json.loads(_VERSION_CACHE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _save_check(data: dict[str, object]) -> None:
    try:
        _VERSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _VERSION_CACHE.write_text(json.dumps(data), encoding='utf-8')
    except OSError:
        pass


def _fetch_latest(timeout: float = 5.0) -> str | None:
    """Последняя версия с PyPI (None — не удалось/нет сети)."""
    req = Request(PYPI_JSON, headers={'User-Agent': 'onec-converter-cli'})
    try:
        with urlopen(req, timeout=timeout) as resp:
            info = json.loads(resp.read().decode('utf-8'))
        return info.get('info', {}).get('version') or None
    except (URLError, OSError, ValueError):
        return None


def latest_version() -> str | None:
    """Последняя версия на PyPI с дисковым кешем на сутки; None — нет сети."""
    saved = _saved_check()
    now = time.time()
    ts = saved.get('ts') if saved else None
    if isinstance(ts, (int, float)) and now - float(ts) < _REFRESH_SECONDS:
        assert saved is not None  # ts не None => saved не None
        return str(saved.get('latest') or '')
    latest = _fetch_latest()
    _save_check({'ts': now, 'latest': latest or ''})
    return latest


def render_version_banner(skip_update_check: bool = False) -> str:
    """Человекочитаемый баннер: версия + уведомление об обновлении."""
    lines = [f'onec-converter MCP-сервер — релиз {current_version()}']
    if skip_update_check:
        lines.append('(проверка обновления отключена через ONEC_NO_UPDATE_CHECK)')
        return '\n'.join(lines)
    latest = latest_version()
    if _is_newer(latest, current_version()):
        lines.append(
            f'  ⚠ Доступна новая версия: {latest}. Обновитесь: '
            'python -m pip install --upgrade onec-converter')
    elif latest:
        lines.append('  ✔ Установлена последняя версия')
    # если сети нет — молчим про обновление (не пугаем)
    return '\n'.join(lines)


def print_version_to_stderr(skip_update_check: bool | None = None,
                            _now: str | None = None) -> None:
    """Печать баннера в stderr (виден в терминале сервера/MCP-клиента).

    Не падает при отсутствии сети и не блокирует старт: таймаут на запрос,
    кеш на сутки. Потокобезопасно — вызывается до mcp.run().
    """
    import sys
    from datetime import UTC

    if skip_update_check is None:
        skip_update_check = os.environ.get('ONEC_NO_UPDATE_CHECK', '') == '1'
    # stderr не используется MCP-протоколом (stdout занят JSON-RPC), поэтому
    # безопасно переключить в utf-8 — кириллица баннера не ломается на
    # cp1251-консолях Windows.
    _re = getattr(sys.stderr, 'reconfigure', None)
    if _re is not None:
        try:
            _re(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    stamp = _now or datetime.now(UTC).strftime('%H:%M:%S')
    banner = render_version_banner(skip_update_check)
    for line in banner.splitlines():
        print(f'[onec-converter {stamp}] {line}', file=sys.stderr, flush=True)
