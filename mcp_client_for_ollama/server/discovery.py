"""Server discovery for MCP Client for Ollama.

This module handles automatic discovery of MCP servers from different sources,
like Claude's configuration files.
"""

import os
import json
from typing import Dict, List, Any, Optional
from ..utils.constants import DEFAULT_CLAUDE_CONFIG

def discover_claude_servers() -> Dict[str, Any]:
    """Discover MCP servers from Claude's configuration.
    
    Returns:
        Dict containing discovered server configurations
    """
    if not os.path.exists(DEFAULT_CLAUDE_CONFIG):
        return {}
        
    try:
        with open(DEFAULT_CLAUDE_CONFIG, 'r') as f:
            config = json.load(f)
        return config.get('mcpServers', {})
    except Exception:
        return {}