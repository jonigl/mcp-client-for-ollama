"""Tests for the `ollmcp mcp add/list/remove` CLI commands."""

import pytest
from typer.testing import CliRunner

from mcp_client_for_ollama.server import registry
from mcp_client_for_ollama.server.cli_commands import mcp_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_scopes(tmp_path, monkeypatch):
    monkeypatch.setattr(registry.constants, "USER_MCP_FILE", str(tmp_path / "mcp.json"))
    monkeypatch.setattr(registry.constants, "LOCAL_MCP_FILE", str(tmp_path / "mcp.local.json"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_add_http_server_user_scope():
    result = runner.invoke(mcp_app, ["add", "--transport", "http", "--scope", "user", "notion", "https://mcp.notion.com/mcp"])
    assert result.exit_code == 0, result.output

    servers = registry.load_scope(registry.SCOPE_USER)
    assert servers == {"notion": {"type": "http", "url": "https://mcp.notion.com/mcp"}}


def test_add_sse_server_with_header():
    result = runner.invoke(mcp_app, ["add", "--transport", "sse", "--scope", "user", "private-api",
                                      "https://api.company.com/sse", "--header", "X-API-Key: secret"])
    assert result.exit_code == 0, result.output

    servers = registry.load_scope(registry.SCOPE_USER)
    assert servers["private-api"] == {
        "type": "sse",
        "url": "https://api.company.com/sse",
        "headers": {"X-API-Key": "secret"},
    }


def test_add_stdio_server_with_env_default_local_scope():
    result = runner.invoke(mcp_app, [
        "add", "--env", "AIRTABLE_API_KEY=YOUR_KEY", "airtable",
        "--", "npx", "-y", "airtable-mcp-server"
    ])
    assert result.exit_code == 0, result.output

    servers = registry.load_scope(registry.SCOPE_LOCAL)
    assert servers["airtable"] == {
        "command": "npx",
        "args": ["-y", "airtable-mcp-server"],
        "env": {"AIRTABLE_API_KEY": "YOUR_KEY"},
    }


def test_add_stdio_requires_command():
    result = runner.invoke(mcp_app, ["add", "no-command"])
    assert result.exit_code != 0
    assert "require a command" in result.output


def test_add_invalid_transport():
    result = runner.invoke(mcp_app, ["add", "--transport", "bogus", "name", "https://example.com"])
    assert result.exit_code != 0
    assert "--transport" in result.output


def test_add_duplicate_name_same_scope_errors():
    runner.invoke(mcp_app, ["add", "--transport", "http", "--scope", "user", "dup", "https://a.example.com"])
    result = runner.invoke(mcp_app, ["add", "--transport", "http", "--scope", "user", "dup", "https://b.example.com"])

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_list_empty():
    result = runner.invoke(mcp_app, ["list"])
    assert result.exit_code == 0
    assert "No MCP servers configured" in result.output


def test_list_shows_servers_by_scope():
    runner.invoke(mcp_app, ["add", "--transport", "http", "--scope", "user", "notion", "https://mcp.notion.com/mcp"])

    result = runner.invoke(mcp_app, ["list"])
    assert result.exit_code == 0
    assert "user" in result.output
    assert "notion" in result.output
    assert "https://mcp.notion.com/mcp" in result.output


def test_remove_server():
    runner.invoke(mcp_app, ["add", "--transport", "http", "--scope", "user", "notion", "https://mcp.notion.com/mcp"])

    result = runner.invoke(mcp_app, ["remove", "notion"])
    assert result.exit_code == 0
    assert "Removed" in result.output
    assert registry.load_scope(registry.SCOPE_USER) == {}


def test_remove_nonexistent_server_errors():
    result = runner.invoke(mcp_app, ["remove", "nope"])
    assert result.exit_code != 0
    assert "No server named" in result.output
