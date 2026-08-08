"""Conformance-тесты MCP-сервера (Фаза 23): E2E через stdio-транспорт.

Проверяют соответствие сервера протоколу MCP из коробки клиента mcp 1.x:
initialize-рукопожатие, tools/list, tools/call, изолированную ошибку
неизвестного тула и жизнеспособность сервера после неё (формат ошибок
JSON-RPC). Запускается как отдельный шаг ворот (scripts/gates.sh conformance)
и в CI — см. docs/playbook.md → «MCP conformance».

Тесты синхронные: каждая проверка запускается через asyncio.run (свой
event loop), что обходит несовместимость pytest-asyncio с anyio task group
внутри mcp-клиента (RuntimeError: exit cancel scope in a different task).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent

SRC = Path(__file__).resolve().parents[1] / 'src'
SERVER_CODE = 'from onec_converter.mcp_server import mcp; mcp.run()'


def _params() -> StdioServerParameters:
    env = dict(os.environ)
    env['PYTHONPATH'] = str(SRC)
    return StdioServerParameters(
        command=sys.executable,
        args=['-c', SERVER_CODE],
        env=env,
    )


def _run(check: object) -> None:
    asyncio.run(check)  # type: ignore[arg-type]


async def _check_initialize() -> None:
    async with stdio_client(_params()) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        assert init.protocolVersion  # например '2025-11-25'
        assert init.serverInfo.name == 'onec-converter'


async def _check_tools_list() -> None:
    async with stdio_client(_params()) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = await s.list_tools()
        names = {t.name for t in tools.tools}
        # реальный реестр: сервисные + пайплайн-тулы
        assert 'pipeline_status' in names
        assert 'query_sql' in names
        assert 'table_sizes' in names
        assert 'compare_structures' in names
        assert 'migrate' in names and 'load_direct' in names
        # сокращение Фазы 29.1: дубли-тулы удалены
        assert 'query_table' not in names
        assert 'table_sizes_report' not in names
        assert 'structure_report' not in names


async def _check_call_tools() -> None:
    async with stdio_client(_params()) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool('tools', {})
        assert res.isError is False
        assert res.content
        # tools() — список JSON-блоков: по одному на тул плейбука
        blocks = [c.text for c in res.content if isinstance(c, TextContent)]
        assert blocks
        first = json.loads(blocks[0])
        assert isinstance(first, dict) and first['name'] == 'init'


async def _check_unknown_tool_isolated() -> None:
    async with stdio_client(_params()) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool('nope_tool_xyz', {})
        assert res.isError is True
        blocks = [c.text for c in res.content if isinstance(c, TextContent)]
        assert blocks and 'nope_tool_xyz' in blocks[0]
        # сервер жив: следующий вызов корректен
        res2 = await s.call_tool('tools', {})
        assert res2.isError is False


async def _check_next_hint() -> None:
    async with stdio_client(_params()) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        res = await s.call_tool('pipeline_status', {})
        assert res.isError is False
        blocks = [c.text for c in res.content if isinstance(c, TextContent)]
        assert blocks
        data = json.loads(blocks[0])
        assert isinstance(data, dict) and 'next' in data
        assert data['next']  # непустая рекомендация


def test_initialize_handshake() -> None:
    """initialize: протокол, имя сервера, capabilities."""
    _run(_check_initialize())


def test_tools_list() -> None:
    """tools/list: ключевые тулы пайплайна на месте, дубли удалены."""
    _run(_check_tools_list())


def test_call_tools() -> None:
    """tools/call: tools() без базы — JSON-ответ без ошибки."""
    _run(_check_call_tools())


def test_unknown_tool_error_isolated() -> None:
    """Неизвестный тул → изолированная ошибка, сервер продолжает работу."""
    _run(_check_unknown_tool_isolated())


def test_next_hint_in_json() -> None:
    """Ответы тулов содержат `next` — рекомендуемую команду плейбука."""
    _run(_check_next_hint())
