"""Test server discovery functionality."""

from mcp_client_for_ollama.server.discovery import process_server_urls, parse_server_config_mapping, deduplicate_servers


def test_process_server_urls():
    """Test that server URL processing works correctly."""
    # Test single URL string
    result = process_server_urls("http://localhost:8000/sse")
    assert len(result) == 1
    assert result[0]["type"] == "sse"
    assert result[0]["url"] == "http://localhost:8000/sse"
    assert result[0]["name"] == "localhost_8000"

    # Test list of URLs
    urls = [
        "http://localhost:8000/sse",
        "https://api.example.com/mcp",
        "http://server1.com:9000/streamable"
    ]
    result = process_server_urls(urls)
    assert len(result) == 3

    # Check SSE detection
    sse_server = next(s for s in result if s["url"] == "http://localhost:8000/sse")
    assert sse_server["type"] == "sse"

    # Check default streamable_http type
    http_server = next(s for s in result if s["url"] == "https://api.example.com/mcp")
    assert http_server["type"] == "streamable_http"

    # Test invalid URLs are filtered out
    invalid_urls = ["not-a-url", "ftp://invalid.com", ""]
    result = process_server_urls(invalid_urls)
    assert len(result) == 0

    # Test empty input
    assert process_server_urls([]) == []
    assert process_server_urls(None) == []


def test_server_url_name_generation():
    """Test that server names are generated correctly from URLs."""
    # Test with path - path doesn't affect name, only hostname matters
    result = process_server_urls("http://localhost:8000/api/mcp")
    assert result[0]["name"] == "localhost_8000"

    # Test with SSE path
    result = process_server_urls("http://localhost:8000/sse")
    assert result[0]["name"] == "localhost_8000"

    # Test without path
    result = process_server_urls("http://localhost:9000")
    assert result[0]["name"] == "localhost_9000"

    # Test with complex host including dots (IP address)
    result = process_server_urls("https://127.0.0.1:8443/mcp/v1")
    assert result[0]["name"] == "127_0_0_1_8443"

    # Test with domain containing dots
    result = process_server_urls("https://api.example.com:8080/mcp")
    assert result[0]["name"] == "api_example_com_8080"


def test_server_name_uniqueness():
    """Test that different hosts get unique names."""
    # Test multiple servers with different hosts
    urls = [
        "http://server1.com/sse",
        "http://server2.com/sse",
        "https://api.example.com:8000/sse"
    ]
    result = process_server_urls(urls)
    assert len(result) == 3

    names = [server["name"] for server in result]
    assert len(set(names)) == 3  # All names should be unique
    assert "server1_com" in names
    assert "server2_com" in names
    assert "api_example_com_8000" in names


def test_same_host_different_types():
    """Test that same host with different server types can coexist."""
    # Note: This creates a name collision but is rare in practice
    urls = [
        "http://localhost:8000/sse",
        "http://localhost:8000/mcp"
    ]
    result = process_server_urls(urls)
    assert len(result) == 2

    # Both have same name but different types
    assert all(server["name"] == "localhost_8000" for server in result)
    types = [server["type"] for server in result]
    assert "sse" in types
    assert "streamable_http" in types


def test_ip_address_name_generation():
    """Test that IP addresses in URLs generate proper names without dots."""
    # This is the specific case that was causing the parsing issue
    result = process_server_urls("http://127.0.0.1:8000/mcp")
    assert result[0]["name"] == "127_0_0_1_8000"

    # Test tool name parsing with the generated name
    tool_name = f"{result[0]['name']}.hello_world"
    server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)

    assert server_name == "127_0_0_1_8000"
    assert actual_tool_name == "hello_world"


def test_server_type_detection():
    """Test that server types are detected correctly."""
    # SSE detection by path
    result = process_server_urls("http://localhost:8000/sse")
    assert result[0]["type"] == "sse"

    # SSE detection by URL content
    result = process_server_urls("http://localhost:8000/api/sse/endpoint")
    assert result[0]["type"] == "sse"

    # Default to streamable_http
    result = process_server_urls("http://localhost:8000/mcp")
    assert result[0]["type"] == "streamable_http"

    # Default to streamable_http for generic URLs
    result = process_server_urls("https://api.example.com")
    assert result[0]["type"] == "streamable_http"


def test_parse_server_config_mapping_normalizes_http_type_aliases():
    """The 'http' and 'streamable-http' type aliases should normalize to streamable_http."""
    mapping = {
        "a": {"type": "http", "url": "https://a.example.com/mcp"},
        "b": {"type": "streamable-http", "url": "https://b.example.com/mcp"},
        "c": {"type": "streamable_http", "url": "https://c.example.com/mcp"},
        "d": {"type": "sse", "url": "https://d.example.com/sse"},
    }
    result = parse_server_config_mapping(mapping)
    by_name = {s["name"]: s for s in result}

    assert by_name["a"]["type"] == "streamable_http"
    assert by_name["b"]["type"] == "streamable_http"
    assert by_name["c"]["type"] == "streamable_http"
    assert by_name["d"]["type"] == "sse"


def test_parse_server_config_mapping_stdio_and_disabled():
    """STDIO entries (no type) parse as 'config'; disabled entries are skipped."""
    mapping = {
        "fs": {"command": "npx", "args": ["-y", "server-filesystem", "."]},
        "off": {"command": "npx", "args": ["-y", "other"], "disabled": True},
    }
    result = parse_server_config_mapping(mapping)

    assert len(result) == 1
    assert result[0]["name"] == "fs"
    assert result[0]["type"] == "config"


def test_deduplicate_servers_keeps_registry_entry_over_url_flag():
    """A registry entry and a `-u` flag for one endpoint are one server.

    The registry entry wins because it carries the name the user chose.
    """
    url = "http://127.0.0.1:8000/mcp"
    servers = [
        {"type": "streamable_http", "name": "unreal-mcp", "url": url, "config": {"url": url}},
        {"type": "streamable_http", "name": "127_0_0_1_8000", "url": url},
    ]
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["unreal-mcp"]
    assert any("duplicate" in n for n in notices)


def test_deduplicate_servers_normalizes_url_before_comparing():
    """Trailing slash and host casing do not make a second server."""
    servers = [
        {"type": "streamable_http", "name": "a", "url": "http://LocalHost:8000/mcp/"},
        {"type": "streamable_http", "name": "b", "url": "http://localhost:8000/mcp"},
    ]
    result, _ = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["a"]


def test_deduplicate_servers_keeps_same_url_on_different_transports():
    """SSE and Streamable HTTP on one URL are genuinely two entries."""
    servers = [
        {"type": "sse", "name": "x", "url": "http://localhost:8000/mcp"},
        {"type": "streamable_http", "name": "y", "url": "http://localhost:8000/mcp"},
    ]
    result, notices = deduplicate_servers(servers)

    assert len(result) == 2
    assert notices == []


def test_deduplicate_servers_renames_colliding_names():
    """Two endpoints that differ only by path must not share a name.

    `process_server_urls` derives the name from netloc alone, so these collide.
    """
    servers = process_server_urls([
        "http://localhost:8000/alpha",
        "http://localhost:8000/beta",
    ])
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["localhost_8000", "localhost_8000-2"]
    assert result[0]["url"].endswith("/alpha")
    assert result[1]["url"].endswith("/beta")
    assert any("Renaming" in n for n in notices)


def test_deduplicate_servers_dedupes_stdio_by_command():
    """The same STDIO command from two scopes is one server."""
    servers = [
        {"type": "config", "name": "fs", "config": {"command": "npx", "args": ["-y", "fs", "."]}},
        {"type": "config", "name": "fs-copy", "config": {"command": "npx", "args": ["-y", "fs", "."]}},
    ]
    result, _ = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["fs"]


def test_deduplicate_servers_keeps_stdio_entries_with_different_env():
    """One command run with two credential sets is two servers.

    Both entries connect today, because their names differ; collapsing them
    would silently drop an account.
    """
    servers = [
        {"type": "config", "name": "github-work", "config": {
            "command": "npx", "args": ["-y", "server-github"],
            "env": {"GITHUB_TOKEN": "work-token"},
        }},
        {"type": "config", "name": "github-personal", "config": {
            "command": "npx", "args": ["-y", "server-github"],
            "env": {"GITHUB_TOKEN": "personal-token"},
        }},
    ]
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["github-work", "github-personal"]
    assert notices == []


def test_deduplicate_servers_dedupes_stdio_with_identical_env():
    """The same command with the same env is still one server."""
    env = {"GITHUB_TOKEN": "token"}
    servers = [
        {"type": "config", "name": "github", "config": {"command": "npx", "args": ["-y", "server-github"], "env": env}},
        {"type": "config", "name": "github-copy", "config": {"command": "npx", "args": ["-y", "server-github"], "env": dict(env)}},
    ]
    result, _ = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["github"]


def test_deduplicate_servers_keeps_http_entries_with_different_headers():
    """Two tenants on one URL differ only by Authorization."""
    url = "https://mcp.example.com/mcp"
    servers = [
        {"type": "streamable_http", "name": "tenant-a", "url": url, "headers": {"Authorization": "Bearer a"}},
        {"type": "streamable_http", "name": "tenant-b", "url": url, "headers": {"Authorization": "Bearer b"}},
    ]
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["tenant-a", "tenant-b"]
    assert notices == []


def test_deduplicate_servers_ignores_header_name_casing():
    """Header names are compared as they are sent: lowercased."""
    url = "https://mcp.example.com/mcp"
    servers = [
        {"type": "streamable_http", "name": "a", "url": url, "headers": {"Authorization": "Bearer x"}},
        {"type": "streamable_http", "name": "b", "url": url, "config": {"headers": {"authorization": "Bearer x"}}},
    ]
    result, _ = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["a"]


def test_deduplicate_servers_handles_list_valued_env():
    """Config JSON permits arrays in env, and the target tuple is a dict key.

    Before the values were serialized, one entry like this raised
    ``TypeError: unhashable type: 'list'`` out of ``deduplicate_servers`` —
    which runs before the per-server ``try/except`` in ``_connect_to_server``,
    so a single malformed entry took down every server instead of just its own.
    """
    servers = [
        {"type": "config", "name": "a", "config": {
            "command": "npx", "args": ["-y", "srv"], "env": {"OPTS": ["--a", "--b"]},
        }},
        {"type": "config", "name": "b", "config": {
            "command": "npx", "args": ["-y", "srv"], "env": {"OPTS": ["--a", "--c"]},
        }},
    ]
    result, notices = deduplicate_servers(servers)

    # Different lists are different targets; equal lists still collapse.
    assert [s["name"] for s in result] == ["a", "b"]
    assert notices == []

    duplicate = [servers[0], {"type": "config", "name": "a-copy", "config": {
        "command": "npx", "args": ["-y", "srv"], "env": {"OPTS": ["--a", "--b"]},
    }}]
    result, _ = deduplicate_servers(duplicate)

    assert [s["name"] for s in result] == ["a"]


def test_deduplicate_servers_handles_list_valued_headers_and_args():
    """The same applies to header values and to args."""
    url = "https://mcp.example.com/mcp"
    servers = [
        {"type": "streamable_http", "name": "a", "url": url, "headers": {"X-Scope": ["read", "write"]}},
        {"type": "streamable_http", "name": "b", "url": url, "headers": {"X-Scope": ["read"]}},
        {"type": "config", "name": "c", "config": {"command": "npx", "args": [{"flag": "-y"}]}},
    ]
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["a", "b", "c"]
    assert notices == []


def test_deduplicate_servers_passes_through_distinct_servers():
    """Unrelated servers are returned untouched, in order."""
    servers = process_server_urls([
        "http://localhost:8000/mcp",
        "http://localhost:9000/mcp",
    ])
    result, notices = deduplicate_servers(servers)

    assert [s["name"] for s in result] == ["localhost_8000", "localhost_9000"]
    assert notices == []
