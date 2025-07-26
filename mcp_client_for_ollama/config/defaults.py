"""Default configuration settings for MCP Client for Ollama.

This module provides default settings and paths used throughout the application.
"""

import os
from ..utils.constants import DEFAULT_MODEL, DEFAULT_CONFIG_FILE, DEFAULT_CONFIG_DIR

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
        },
        "modelSettings": {
            "thinkingMode": True,
            "showThinking": False
        },
        "modelConfig": {
            "system_prompt": "",
            "num_keep": None,
            "seed": None,
            "num_predict": None,
            "top_k": None,
            "top_p": None,
            "min_p": None,
            "typical_p": None,
            "repeat_last_n": None,
            "temperature": None,
            "repeat_penalty": None,
            "presence_penalty": None,
            "frequency_penalty": None,
            "stop": None
        },
        "displaySettings": {
            "showToolExecution": True,
            "showMetrics": False
        },
        "hilSettings": {
            "enabled": True
        }
    }

def get_config_path(config_name: str = "default") -> str:
    """Get the path to a specific configuration file.

    Args:
        config_name: Name of the configuration (default: "default")

    Returns:
        str: Path to the configuration file
    """
    # Ensure the directory exists
    os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)

    # Sanitize the config name
    config_name = ''.join(c for c in config_name if c.isalnum() or c in ['-', '_']).lower() or "default"

    if config_name == "default":
        return os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
    else:
        return os.path.join(DEFAULT_CONFIG_DIR, f"{config_name}.json")
