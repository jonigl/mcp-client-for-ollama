"""MCP server registry for MCP Client for Ollama.

Reads and writes the scoped server configuration files managed by the
``ollmcp mcp add/list/remove`` commands. Three scopes are supported, mirroring
Claude Code:

- ``local``   - private to the current project, stored under the current working
                directory key in ``~/.config/ollmcp/mcp.local.json``.
- ``project`` - shareable ``.mcp.json`` at the project root (current directory).
- ``user``    - global, stored in ``~/.config/ollmcp/mcp.json``.

When the same server name exists in more than one scope, precedence is
``local`` > ``project`` > ``user`` (the whole entry from the highest-precedence
scope is used; fields are not merged across scopes).
"""

import json
import os
from typing import Any, Dict, List, Optional

from ..utils import constants

SCOPE_LOCAL = "local"
SCOPE_PROJECT = "project"
SCOPE_USER = "user"

# Ordered from lowest to highest precedence so later scopes override earlier ones.
SCOPES = [SCOPE_USER, SCOPE_PROJECT, SCOPE_LOCAL]


def _read_json(path: str) -> Dict[str, Any]:
    """Read a JSON file, returning an empty dict if missing or invalid."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(path: str, data: Dict[str, Any]) -> None:
    """Write data as pretty-printed JSON, creating parent directories."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def scope_path(scope: str) -> str:
    """Return the file path backing a scope (computed at call time)."""
    if scope == SCOPE_USER:
        return constants.USER_MCP_FILE
    if scope == SCOPE_LOCAL:
        return constants.LOCAL_MCP_FILE
    if scope == SCOPE_PROJECT:
        return os.path.join(os.getcwd(), constants.PROJECT_MCP_FILENAME)
    raise ValueError(f"Unknown scope: {scope}")


def load_scope(scope: str) -> Dict[str, Any]:
    """Return the ``mcpServers`` mapping for a scope ({} if none)."""
    data = _read_json(scope_path(scope))
    if scope == SCOPE_LOCAL:
        projects = data.get("projects", {})
        return projects.get(os.getcwd(), {}).get("mcpServers", {})
    return data.get("mcpServers", {})


def add_server(scope: str, name: str, entry: Dict[str, Any]) -> None:
    """Add or update a server entry in the given scope's file."""
    path = scope_path(scope)
    data = _read_json(path)

    if scope == SCOPE_LOCAL:
        cwd = os.getcwd()
        projects = data.setdefault("projects", {})
        project = projects.setdefault(cwd, {})
        servers = project.setdefault("mcpServers", {})
        servers[name] = entry
    else:
        servers = data.setdefault("mcpServers", {})
        servers[name] = entry

    _write_json(path, data)


def remove_server(name: str, scope: Optional[str] = None) -> Optional[str]:
    """Remove a server by name.

    If ``scope`` is given, only that scope is searched. Otherwise scopes are
    searched in precedence order (local > project > user) and the first match
    is removed.

    Returns the scope the server was removed from, or None if not found.
    """
    search = [scope] if scope else list(reversed(SCOPES))
    for sc in search:
        path = scope_path(sc)
        data = _read_json(path)

        if sc == SCOPE_LOCAL:
            servers = data.get("projects", {}).get(os.getcwd(), {}).get("mcpServers", {})
        else:
            servers = data.get("mcpServers", {})

        if name in servers:
            del servers[name]
            _write_json(path, data)
            return sc
    return None


def list_by_scope() -> Dict[str, Dict[str, Any]]:
    """Return each scope's ``mcpServers`` mapping keyed by scope name."""
    return {scope: load_scope(scope) for scope in SCOPES}


def merge_scopes() -> Dict[str, Any]:
    """Merge all scopes into a single ``mcpServers`` mapping.

    Honors precedence local > project > user: when a name appears in multiple
    scopes the higher-precedence entry wins (used at startup).
    """
    merged: Dict[str, Any] = {}
    for scope in SCOPES:  # user -> project -> local; later overrides earlier
        merged.update(load_scope(scope))
    return merged
