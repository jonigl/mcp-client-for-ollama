"""Server discovery for MCP Client for Ollama.

This module handles automatic discovery of MCP servers from different sources,
like Claude's configuration files.
"""

import os
import json
from typing import Dict, List, Any
from urllib.parse import urlparse
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

def load_claude_desktop_servers() -> List[Dict[str, Any]]:
    """Load server configurations from Claude Desktop's config file.

    Returns:
        List of server configurations found in Claude Desktop's config
    """
    return parse_server_configs(DEFAULT_CLAUDE_CONFIG)
