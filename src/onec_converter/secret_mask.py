"""Маскирование секретов в строках DSN/URL (Фаза 52, U8/U27).

Пароли и токены в `--source-url`/DSN не должны попадать в журналы,
исключения и отчёты. Покрываем:
  - user:password@host        (URL userinfo)
  - password=PWD / pwd=PWD
  - token=TOK / client_secret=CS / secret=SK / access_key=AK / key=K
  - ?__token=... query-параметры
Значения заменяются на '***'. Код авторский, независимый.
"""

from __future__ import annotations

import re

# ключ=значение (значение до '&' или конца)
_KEY_VALUE = re.compile(
    r'(password|pwd|passwd|token|client_secret|secret|access_key|secret_key'
    r'|apikey|api_key|key)\s*=\s*([^&\s;,)]+)',
    re.IGNORECASE,
)
# URL userinfo: scheme://user:pass@host  или user:pass@host
_USERINFO = re.compile(r'(?P<pre>://[^/@\s:]+:)[^/@\s@]+(?P<post>@)')


def mask_secrets(text: str) -> str:
    """Заменить секреты (userinfo, key=...) в строке на '***'."""
    if not text:
        return text
    out = _USERINFO.sub(r'\g<pre>***\g<post>', text)
    out = _KEY_VALUE.sub(lambda m: f'{m.group(1)}=***', out)
    return out


def mask_dsn(dsn: str) -> str:
    """Маскировать DSN PostgreSQL: postgresql://user:pass@host/db -> ***."""
    return mask_secrets(dsn)
