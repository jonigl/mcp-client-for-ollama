"""Tests for the scoped MCP server registry used by `ollmcp mcp add/list/remove`."""

import os

import pytest

from mcp_client_for_ollama.server import registry


@pytest.fixture(autouse=True)
def _isolated_scopes(tmp_path, monkeypatch):
    """Point all scope files at a temp directory and cwd."""
    monkeypatch.setattr(registry.constants, "USER_MCP_FILE", str(tmp_path / "mcp.json"))
    monkeypatch.setattr(registry.constants, "LOCAL_MCP_FILE", str(tmp_path / "mcp.local.json"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_add_and_load_user_scope(tmp_path):
    registry.add_server(registry.SCOPE_USER, "notion", {"type": "http", "url": "https://mcp.notion.com/mcp"})

    servers = registry.load_scope(registry.SCOPE_USER)
    assert servers == {"notion": {"type": "http", "url": "https://mcp.notion.com/mcp"}}

    # Written as standard {"mcpServers": {...}}
    import json
    with open(registry.constants.USER_MCP_FILE) as f:
        data = json.load(f)
    assert data == {"mcpServers": {"notion": {"type": "http", "url": "https://mcp.notion.com/mcp"}}}


def test_add_and_load_project_scope(tmp_path):
    registry.add_server(registry.SCOPE_PROJECT, "gh", {"type": "http", "url": "https://api.githubcopilot.com/mcp/"})

    servers = registry.load_scope(registry.SCOPE_PROJECT)
    assert servers == {"gh": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"}}

    # Written as a standard top-level {"mcpServers": {...}} .mcp.json (no extra
    # nesting, unlike local scope) so it's readable by Claude Code and other tools.
    project_file = os.path.join(os.getcwd(), ".mcp.json")
    assert os.path.exists(project_file)
    import json
    with open(project_file) as f:
        data = json.load(f)
    assert data == {"mcpServers": {"gh": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"}}}


def test_add_and_load_local_scope_keyed_by_cwd(tmp_path):
    registry.add_server(registry.SCOPE_LOCAL, "fs", {"command": "npx", "args": ["-y", "server-fs", "."]})

    servers = registry.load_scope(registry.SCOPE_LOCAL)
    assert servers == {"fs": {"command": "npx", "args": ["-y", "server-fs", "."]}}

    import json
    with open(registry.constants.LOCAL_MCP_FILE) as f:
        data = json.load(f)
    cwd = os.getcwd()
    assert data["projects"][cwd]["mcpServers"]["fs"]["command"] == "npx"


def test_merge_scopes_precedence_local_over_project_over_user():
    registry.add_server(registry.SCOPE_USER, "dup", {"type": "http", "url": "https://user.example.com"})
    registry.add_server(registry.SCOPE_PROJECT, "dup", {"type": "http", "url": "https://project.example.com"})
    registry.add_server(registry.SCOPE_LOCAL, "dup", {"type": "http", "url": "https://local.example.com"})

    merged = registry.merge_scopes()
    assert merged["dup"]["url"] == "https://local.example.com"


def test_merge_scopes_combines_distinct_names():
    registry.add_server(registry.SCOPE_USER, "a", {"type": "http", "url": "https://a.example.com"})
    registry.add_server(registry.SCOPE_PROJECT, "b", {"type": "http", "url": "https://b.example.com"})
    registry.add_server(registry.SCOPE_LOCAL, "c", {"command": "npx", "args": []})

    merged = registry.merge_scopes()
    assert set(merged.keys()) == {"a", "b", "c"}


def test_merge_scopes_empty_when_nothing_configured():
    assert registry.merge_scopes() == {}


def test_remove_server_without_scope_falls_through_to_lower_precedence_scope():
    registry.add_server(registry.SCOPE_USER, "only-user", {"type": "http", "url": "https://u.example.com"})

    found = registry.remove_server("only-user")
    assert found == registry.SCOPE_USER
    assert registry.load_scope(registry.SCOPE_USER) == {}


def test_remove_server_without_scope_removes_highest_precedence_match_when_duplicated():
    registry.add_server(registry.SCOPE_USER, "dup", {"type": "http", "url": "https://user.example.com"})
    registry.add_server(registry.SCOPE_PROJECT, "dup", {"type": "http", "url": "https://project.example.com"})
    registry.add_server(registry.SCOPE_LOCAL, "dup", {"type": "http", "url": "https://local.example.com"})

    found = registry.remove_server("dup")
    assert found == registry.SCOPE_LOCAL
    assert "dup" not in registry.load_scope(registry.SCOPE_LOCAL)

    # Lower-precedence entries with the same name are untouched
    assert registry.load_scope(registry.SCOPE_PROJECT)["dup"]["url"] == "https://project.example.com"
    assert registry.load_scope(registry.SCOPE_USER)["dup"]["url"] == "https://user.example.com"


def test_remove_server_with_explicit_scope():
    registry.add_server(registry.SCOPE_USER, "x", {"type": "http", "url": "https://x.example.com"})
    registry.add_server(registry.SCOPE_PROJECT, "x", {"type": "http", "url": "https://x.example.com"})

    found = registry.remove_server("x", scope=registry.SCOPE_PROJECT)
    assert found == registry.SCOPE_PROJECT
    assert "x" not in registry.load_scope(registry.SCOPE_PROJECT)
    assert "x" in registry.load_scope(registry.SCOPE_USER)


def test_remove_server_not_found_returns_none():
    assert registry.remove_server("does-not-exist") is None
    assert registry.remove_server("does-not-exist", scope=registry.SCOPE_USER) is None


def test_list_by_scope():
    registry.add_server(registry.SCOPE_USER, "u", {"type": "http", "url": "https://u.example.com"})
    registry.add_server(registry.SCOPE_PROJECT, "p", {"type": "http", "url": "https://p.example.com"})

    by_scope = registry.list_by_scope()
    assert by_scope[registry.SCOPE_USER] == {"u": {"type": "http", "url": "https://u.example.com"}}
    assert by_scope[registry.SCOPE_PROJECT] == {"p": {"type": "http", "url": "https://p.example.com"}}
    assert by_scope[registry.SCOPE_LOCAL] == {}
