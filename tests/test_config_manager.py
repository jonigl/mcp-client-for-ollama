"""Tests for configuration manager. Copyright 2026 ITTH GmbH & Co. KG"""

from mcp_client_for_ollama.config.manager import ConfigManager
from mcp_client_for_ollama.config.defaults import default_config
from rich.console import Console


def test_validate_config_preserves_host():
    """Test that _validate_config preserves the host field from loaded config."""
    mgr = ConfigManager(Console())

    config_data = {
        "host": "http://remote-server:11434",
        "model": "test-model"
    }

    validated = mgr._validate_config(config_data)

    assert validated["host"] == "http://remote-server:11434"


def test_validate_config_omits_host_when_missing():
    """Test that _validate_config omits host when not in config file.

    This allows CLI arguments to take precedence over defaults when
    the config file doesn't have a host field (e.g., older config files).
    """
    mgr = ConfigManager(Console())

    config_data = {
        "model": "test-model"
    }

    validated = mgr._validate_config(config_data)

    # Host should NOT be in the validated config when not in original
    # This allows CLI arguments to take precedence
    assert "host" not in validated


def test_default_config_shows_thinking_text():
    """Test that thinking text is visible by default in new configurations."""
    config = default_config()

    assert config["modelSettings"]["showThinking"] is True
