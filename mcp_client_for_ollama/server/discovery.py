"""Server discovery for MCP Client for Ollama.

This module handles automatic discovery of MCP servers from different sources,
like Claude's configuration files.
"""

import os
import json
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse, urlunparse
from ..utils.constants import DEFAULT_CLAUDE_CONFIG

def process_server_paths(server_paths) -> List[Dict[str, Any]]:
    """Process individual server script paths and validate them.

    Args:
        server_paths: A string or list of paths to server scripts

    Returns:
        List of valid server configurations ready to be connected to
    """
    if not server_paths:
        return []

    # Convert single string to list
    if isinstance(server_paths, str):
        server_paths = [server_paths]

    all_servers = []
    for path in server_paths:
        # Check if the path exists and is a file
        if not os.path.exists(path):
            continue

        if not os.path.isfile(path):
            continue

        # Create server entry
        all_servers.append({
            "type": "script",
            "path": path,
            "name": os.path.basename(path).split('.')[0]  # Use filename without extension as name
        })

    return all_servers

def process_server_urls(server_urls) -> List[Dict[str, Any]]:
    """Process individual server URLs and create configurations for SSE/HTTP servers.

    Args:
        server_urls: A string or list of URLs to server endpoints

    Returns:
        List of valid server configurations ready to be connected to
    """
    if not server_urls:
        return []

    # Convert single string to list
    if isinstance(server_urls, str):
        server_urls = [server_urls]

    all_servers = []
    for url in server_urls:
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            continue

        # Extract a meaningful name from the URL
        parsed = urlparse(url)

        # Use hostname but replace dots and colons with underscores to avoid parsing issues
        name = parsed.netloc.replace(':', '_').replace('.', '_')

        # Determine server type based on URL patterns
        server_type = "streamable_http"  # Default to streamable_http
        if "sse" in url.lower() or "/sse" in parsed.path.lower():
            server_type = "sse"

        # Create server entry with clean hostname-based name
        all_servers.append({
            "type": server_type,
            "url": url,
            "name": name
        })

    return all_servers

# Aliases for the Streamable HTTP transport accepted in config "type" fields.
# ollmcp uses "streamable_http" internally; the cross-tool .mcp.json standard and
# Claude Code use "http" / "streamable-http". Normalize them all so externally
# authored configs (and our own writes) parse correctly.
_HTTP_TYPE_ALIASES = {"http", "streamable-http", "streamable_http"}


def parse_server_config_mapping(server_configs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse and validate a mapping of MCP server configurations.

    Args:
        server_configs: The ``mcpServers`` mapping ({name: entry, ...})

    Returns:
        List of valid server configurations ready to be connected to
    """
    all_servers = []

    for name, config in server_configs.items():
        # Skip disabled servers
        if config.get('disabled', False):
            continue

        # Determine server type
        server_type = "config"  # Default type for STDIO servers

        # Check for URL-based server types (sse or streamable_http)
        if "type" in config:
            # Type is explicitly specified in config; normalize HTTP aliases
            raw_type = config["type"]
            server_type = "streamable_http" if raw_type in _HTTP_TYPE_ALIASES else raw_type
        elif "url" in config:
            # URL exists but no type, default to streamable_http
            server_type = "streamable_http"

        # Create server config object
        server = {
            "type": server_type,
            "name": name,
            "config": config
        }

        # For URL-based servers, add direct access to URL and headers
        if server_type in ["sse", "streamable_http"]:
            server["url"] = config.get("url")
            if "headers" in config:
                server["headers"] = config.get("headers")

        all_servers.append(server)

    return all_servers


def parse_server_configs(config_path: str) -> List[Dict[str, Any]]:
    """Parse and validate server configurations from a file.

    Args:
        config_path: Path to JSON config file

    Returns:
        List of valid server configurations ready to be connected to
    """
    if not config_path or not os.path.exists(config_path):
        return []

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return parse_server_config_mapping(config.get('mcpServers', {}))

    except Exception:
        # Return empty list on error
        return []

def _server_target(server: Dict[str, Any]) -> tuple:
    """Identify the endpoint a server entry points at.

    Two entries with the same target are one server reached from two sources
    (e.g. the registry and a ``-u`` flag), not two servers. The transport is
    part of the target, so the same URL served over SSE and Streamable HTTP
    stays two distinct entries.
    """
    server_type = server.get("type", "script")

    url = server.get("url")
    if url:
        parsed = urlparse(url)
        # Case in scheme/host is not meaningful, a trailing slash is not either,
        # and the fragment never reaches the server.
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            parsed.query,
            "",
        ))
        return (server_type, normalized)

    path = server.get("path")
    if path:
        return ("script", os.path.abspath(path))

    config = server.get("config") or {}
    command = config.get("command")
    if command:
        return ("stdio", command, tuple(config.get("args") or []))

    return ("name", server.get("name"))


def deduplicate_servers(servers: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Collapse duplicate entries and make the remaining names unique.

    Server entries arrive from five independent sources, so the same endpoint
    can appear more than once, and names derived from a URL's netloc can
    collide for endpoints that differ only by path. Both cases used to end with
    one connection silently overwriting another in ``ServerConnector.sessions``
    while the overwritten server's tools stayed advertised to the model.

    Args:
        servers: Server configurations, in source precedence order

    Returns:
        Tuple of (servers, notices) where notices are human-readable messages
        about what was dropped or renamed
    """
    notices = []

    # Same endpoint from two sources: keep the first, which is the entry from
    # the more explicit source (a registry name beats a name derived from a URL).
    unique = []
    seen: Dict[tuple, str] = {}
    for server in servers:
        target = _server_target(server)
        if target in seen:
            notices.append(
                f"Skipping duplicate entry '{server.get('name')}': "
                f"same server as '{seen[target]}'"
            )
            continue
        seen[target] = server.get("name")
        unique.append(server)

    # Distinct endpoints that resolved to the same name: disambiguate instead
    # of letting the later one overwrite the earlier one.
    result = []
    used = set()
    for server in unique:
        name = server.get("name")
        if name in used:
            suffix = 2
            while f"{name}-{suffix}" in used:
                suffix += 1
            new_name = f"{name}-{suffix}"
            notices.append(
                f"Renaming '{name}' to '{new_name}': another server already uses that name"
            )
            server = {**server, "name": new_name}
            name = new_name
        used.add(name)
        result.append(server)

    return result, notices


def load_claude_desktop_servers() -> List[Dict[str, Any]]:
    """Load server configurations from Claude Desktop's config file.

    Returns:
        List of server configurations found in Claude Desktop's config
    """
    return parse_server_configs(DEFAULT_CLAUDE_CONFIG)
