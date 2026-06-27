"""Default configuration settings for MCP Client for Ollama.

This module provides default settings and paths used throughout the application.
"""

import os
from ..utils.constants import DEFAULT_MODEL, DEFAULT_CONFIG_FILE, DEFAULT_CONFIG_DIR, DEFAULT_OLLAMA_HOST

def default_provider_profile(provider: str = "ollama") -> dict:
    """Get the default connection profile for a provider.

    Args:
        provider: Provider name (e.g., "ollama", "openai")

    Returns:
        dict: Default per-provider connection identity (host, model, apiKey).
              An empty host means "use the provider's own default endpoint";
              for ollama we seed the local default. An empty model means
              "resolve to the first available model at startup".
    """
    return {
        "host": DEFAULT_OLLAMA_HOST if provider == "ollama" else "",
        "model": DEFAULT_MODEL if provider == "ollama" else "",
        "apiKey": "",
    }


def default_config() -> dict:
    """Get default configuration settings.

    Returns:
        dict: Default configuration dictionary
    """

    return {
        "defaultProvider": "ollama",
        "providers": {
            "ollama": default_provider_profile("ollama"),
        },
        "enabledTools": {},  # Will be populated with available tools
        "contextSettings": {
            "retainContext": True
        },
        "modelSettings": {
            "thinkingMode": True,
            "showThinking": True
        },
        "agentSettings": {
            "loopLimit": 7
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
            "stop": None,
            "num_ctx": None,
            "num_batch" : None
        },
        "displaySettings": {
            "showToolExecution": True,
            "showMetrics": False,
            "answerRenderMode": "both"
        },
        "inputSettings": {
            "inputMode": "single"
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
