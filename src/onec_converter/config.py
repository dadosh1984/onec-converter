"""Конфигурация проекта : читает onec.toml в каталоге проекта/текущей папке.

Повторяющиеся параметры CLI (кодировка источника, лимиты, tmp-каталог)
могут задаваться в файле, чтобы не повторять длинные флаги.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Кодировка источника по умолчанию для 7.7 (CP866) — единый источник,
# вместо хардкода 'cp866' в нескольких местах (аудит раунда 6, B6).
DEFAULT_SOURCE_ENCODING = 'cp866'


@dataclass
class ProjectConfig:
    """Значения по умолчанию из конфиг-файла (onec.toml)."""

    source_encoding: str = DEFAULT_SOURCE_ENCODING
    limit: int = 0
    rules_file: str = ''
    target_url: str = ''
    retries: int = 3
    tmp_dir: str = ''
    # аутентификация приёмника (): OAuth2 client-credentials
    token_url: str = ''
    client_id: str = ''
    client_secret: str = ''
    secret: str = ''  # общий секрет mint-token ()
    # прочие ключи сохраняются как есть
    _raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> ProjectConfig:
        cfg = cls()
        p = Path(path) if path else _find_config()
        if p is None or not p.is_file():
            return cfg
        parser = configparser.ConfigParser()
        # onec.toml может быть без секций (упрощённый INI) или с [onec]
        try:
            parser.read(p, encoding='utf-8')
        except (configparser.Error, OSError, UnicodeDecodeError):
            return cfg
        sec = parser['onec'] if parser.has_section('onec') else parser.defaults()
        for src, attr in [
            ('source_encoding', 'source_encoding'),
            ('limit', 'limit'),
            ('rules_file', 'rules_file'),
            ('target_url', 'target_url'),
            ('retries', 'retries'),
            ('tmp_dir', 'tmp_dir'),
        ]:
            if src in sec:
                val = sec[src].strip().strip('"').strip()
                try:
                    if attr in ('limit', 'retries'):
                        setattr(cfg, attr, int(val))
                    else:
                        setattr(cfg, attr, val)
                except ValueError:
                    pass
        # секция [auth] — OAuth2-параметры приёмника ()
        auth = parser['auth'] if parser.has_section('auth') else sec
        for src, attr in [('token_url', 'token_url'),
                          ('client_id', 'client_id'),
                          ('client_secret', 'client_secret'),
                          ('secret', 'secret')]:
            if src in auth:
                setattr(cfg, attr, auth[src].strip().strip('"').strip())
        cfg._raw = {k: sec[k] for k in sec}
        return cfg

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {'source_encoding': self.source_encoding,
                             'limit': self.limit, 'rules_file': self.rules_file,
                             'target_url': self.target_url, 'retries': self.retries,
                             'tmp_dir': self.tmp_dir,
                             'token_url': self.token_url, 'client_id': self.client_id,
                             'client_secret': self.client_secret, 'secret': self.secret}
        return d


def _find_config() -> Path | None:
    """Поиск onec.toml: текущая папка и выше до корня."""
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        p = d / 'onec.toml'
        if p.is_file():
            return p
    return None
