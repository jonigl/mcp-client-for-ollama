"""Server discovery for MCP Client for Ollama.

This module handles automatic discovery of MCP servers from different sources,
like Claude's configuration files.
"""

import os
import json
from typing import Dict, List, Any, Optional
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

def parse_server_configs(config_path: str) -> List[Dict[str, Any]]:
    """Parse and validate server configurations from a file.
    
    Args:
        config_path: Path to JSON config file
        
    Returns:
        List of valid server configurations ready to be connected to
    """
    all_servers = []
    
    if not config_path or not os.path.exists(config_path):
        return all_servers
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        server_configs = config.get('mcpServers', {})
        
        for name, config in server_configs.items():
            # Skip disabled servers
            if config.get('disabled', False):
                continue
                
            all_servers.append({
                "type": "config",
                "name": name,
                "config": config
            })
            
        return all_servers
        
    except Exception as e:
        # Return empty list on error
        return []

def auto_discover_servers() -> List[Dict[str, Any]]:
    """Automatically discover available server configurations.
    
    Currently only discovers from Claude's config.
    
    Returns:
        List of server configurations found automatically
    """
    # Use parse_server_configs to process Claude's config
    return parse_server_configs(DEFAULT_CLAUDE_CONFIG)
