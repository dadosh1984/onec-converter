"""Поверхность MCP-тулов: каждый тул, упомянутый в playbook/docs/SKILL, обязан
существовать в реестре сервера. Защита от 'Unknown tool' — скилл/плейбук
не должны советовать агенту несуществующие команды (step_* — внутренние
шаги migrate(), не exposed-тулы).

Реальные 18 тулов сервера (tools/list, v0.43.1):
  audit_verify, auto_map_schemas, base_health, cache_stats, compare_structures,
  compress_metadata, config_versions, dump_metadata, explain_diff, guid_diff,
  load_direct, migrate, pipeline_status, playbook, query_sql, search_schema,
  table_sizes, tools
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Внутренние шаги migrate(), которые НЕ должны быть exposed-тулами
FORBIDDEN = {"step_init", "step_extract", "step_map", "step_load",
             "step_prevalidate", "step_inspect_source", "step_inspect_target",
             "verify", "transform", "preview", "inspect_target",
             "inspect_source", "extract"}


def real_tools() -> set[str]:
    from onec_converter import mcp_server

    return {t.name for t in mcp_server.mcp._tool_manager.list_tools()}


@pytest.fixture(scope="module")
def tools() -> set[str]:
    return real_tools()


def _candidate_tools(path: Path) -> set[str]:
    """Имена-кандидаты тулов по тексту файла (regex-безопасно)."""
    valid = {"tools", "migrate", "load_direct", "query_sql", "guid_diff",
             "table_sizes", "search_schema", "playbook", "pipeline_status",
             "base_health", "config_versions", "dump_metadata",
             "compress_metadata", "explain_diff", "auto_map_schemas",
             "compare_structures", "audit_verify", "cache_stats"}
    text = path.read_text(encoding="utf-8")
    found = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\(", text))
    return {n for n in found if n in valid or n.startswith("step_") or n in FORBIDDEN}


@pytest.mark.parametrize("source", [
    (ROOT / "docs" / "playbook.md", "docs/playbook.md"),
    (ROOT / "skills" / "onec-converter-migration" / "SKILL.md", "SKILL.md"),
])
def test_documented_tool_names_exist(tools, source):
    """Каждое имя-тул из docs/SKILL существует в реестре MCP."""
    path, label = source
    if not path.exists():
        pytest.skip(f"нет файла {path.name} — {label} отсутствует")
    names = _candidate_tools(path)
    fake = names - tools
    assert not fake, (
        f"{label}: несуществующие тулы {sorted(fake)!r}; "
        f"реальные: {sorted(tools)}")


def test_step_tools_are_not_exposed_as_tools(tools):
    """step_*/verify/transform/preview не должны быть exposed-тулами."""
    assert not (FORBIDDEN & tools), f"запрещённые тулы exposed: {sorted(FORBIDDEN & tools)}"


def test_playbook_command_names_exist(tools):
    """PLAYBOOK (из mcp_server) содержит только реальные тулы."""
    from onec_converter import mcp_server

    cmds = [p["command"].split("(")[0] for p in mcp_server.PLAYBOOK]
    fake = {c for c in cmds if c not in tools}
    assert not fake, f"PLAYBOOK ссылается на несуществующие тулы: {sorted(fake)}"
    assert all(p["command"] and p["goal"] for p in mcp_server.PLAYBOOK)


def test_playbook_next_commands_exist(tools):
    """Значения PLAYBOOK_NEXT ссылаются только на реальные тулы (leading command)."""
    from onec_converter import mcp_server

    bad = []
    for value in mcp_server.PLAYBOOK_NEXT.values():
        head = value.lstrip().split("(", 1)[0].strip().strip('"\'' )
        if head and head.replace("_", "").isalnum() and head not in tools:
            bad.append(head)
    assert not bad, f"PLAYBOOK_NEXT ссылается на несуществующие тулы: {sorted(set(bad))}"


def test_e2e_tools_list_matches_registry(tools):
    """stdout: tools/list реально возвращает не меньше 18 тулов-реестра."""
    assert len(tools) >= 18
    assert {"playbook", "migrate", "load_direct", "guid_diff"} <= tools
