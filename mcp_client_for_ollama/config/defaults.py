"""Default configuration settings for MCP Client for Ollama.

This module provides default settings and paths used throughout the application.
"""

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