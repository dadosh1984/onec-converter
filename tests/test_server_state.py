"""Тесты ServerState — изоляция, мета-кеш, contextvars."""

from __future__ import annotations

import pytest

from onec_converter.server_state import (
    ServerState,
    get_server_state,
    reset_server_state,
    set_server_state,
)


def test_server_state_meta():
    state = ServerState()
    state.set_meta("version", "1.0.0")
    assert state.get_meta("version") == "1.0.0"
    assert state.get_meta("missing") is None
    assert state.get_meta("missing", "default") == "default"


def test_server_state_update():
    state = ServerState()
    state.update_meta({"a": 1, "b": 2})
    assert state.get_meta("a") == 1
    assert state.get_meta("b") == 2


def test_get_server_state_without_context():
    """Вне lifespan — None."""
    reset_server_state(set_server_state(ServerState()))
    reset_server_state(set_server_state(None))
    assert get_server_state() is None


def test_get_server_state_with_context():
    state = ServerState()
    token = set_server_state(state)
    try:
        assert get_server_state() is state
    finally:
        reset_server_state(token)
    assert get_server_state() is None


def test_server_state_isolation():
    """Два разных ServerState не пересекаются."""
    s1 = ServerState()
    s1.set_meta("key", "from_s1")
    t1 = set_server_state(s1)
    s2 = ServerState()
    s2.set_meta("key", "from_s2")
    t2 = set_server_state(s2)
    try:
        # s2 active
        assert get_server_state() is s2
        assert get_server_state().get_meta("key") == "from_s2"
        reset_server_state(t2)
        # s1 restored
        assert get_server_state() is s1
        assert get_server_state().get_meta("key") == "from_s1"
    finally:
        reset_server_state(t1)
