"""Default configuration settings for MCP Client for Ollama.

This module provides default settings and paths used throughout the application.
"""

import os
from ..utils.constants import DEFAULT_MODEL

def default_config() -> dict:
    """Get default configuration settings.
    
    Returns:
        dict: Default configuration dictionary
    """
    return {
        "model": DEFAULT_MODEL,
        "enabledTools": {},  # Will be populated with available tools
        "contextSettings": {
            "retainContext": True
        }
    }
    
def get_config_dir() -> str:
    """Get the configuration directory path.
    
    Returns:
        str: Path to the configuration directory
    """
    from ..utils.constants import DEFAULT_CONFIG_DIR
    
    # Ensure the directory exists
    os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
    return DEFAULT_CONFIG_DIR
    
def get_config_path(config_name: str = "default") -> str:
    """Get the path to a specific configuration file.
    
    Args:
        config_name: Name of the configuration (default: "default")
        
    Returns:
        str: Path to the configuration file
    """
    from ..utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE
    
    config_dir = get_config_dir()
    
    # Sanitize the config name
    config_name = ''.join(c for c in config_name if c.isalnum() or c in ['-', '_']).lower() or "default"
    
    if config_name == "default":
        return os.path.join(config_dir, DEFAULT_CONFIG_FILE)
    else:
        return os.path.join(config_dir, f"{config_name}.json")
