"""Server-scoped state для MCP через ContextVar.

Явное состояние, инициализируемое через lifespan MCP-сервера.
Доступно из любого тула через get_server_state().
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServerState:
    """Явное состояние MCP-сервера. Живёт весь lifespan приложения."""

    meta_cache: dict[str, Any] = field(default_factory=dict)

    def get_meta(self, key: str, default: Any = None) -> Any:
        return self.meta_cache.get(key, default)

    def set_meta(self, key: str, value: Any) -> None:
        self.meta_cache[key] = value

    def update_meta(self, updates: dict[str, Any]) -> None:
        self.meta_cache.update(updates)


_server_state_ctx: contextvars.ContextVar[ServerState | None] = (
    contextvars.ContextVar("server_state_ctx", default=None)
)


def get_server_state() -> ServerState | None:
    """ServerState текущего контекста lifespan.

    Возвращает None если lifespan не инициализирован.
    """
    return _server_state_ctx.get()


def set_server_state(state: ServerState) -> contextvars.Token:
    """Установить ServerState в контекст (вызывается из lifespan)."""
    return _server_state_ctx.set(state)


def reset_server_state(token: contextvars.Token) -> None:
    """Восстановить предыдущий контекст."""
    _server_state_ctx.reset(token)
