"""Configuration management for MCP Client for Ollama.

This module handles loading, saving, and validating configuration settings for
the MCP Client for Ollama, including tool settings and model preferences.
"""

import json
import os
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from ..utils.constants import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE
from .defaults import default_config

class ConfigManager:
    """Manages configuration for the MCP Client for Ollama.

    This class handles loading, saving, and validating configuration settings,
    including enabled tools, selected model, and context retention preferences.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the ConfigManager.

        Args:
            console: Rich console for output (optional)
        """
        self.console = console or Console()

    def config_exists(self, config_name: Optional[str] = None) -> bool:
        """Check if a configuration file exists without printing messages.

        Args:
            config_name: Optional name of the config to check (defaults to 'default')

        Returns:
            bool: True if the configuration file exists, False otherwise
        """
        # Default to 'default' if no config name provided
        if not config_name:
            config_name = "default"

        # Sanitize filename
        config_name = self._sanitize_config_name(config_name)

        # Create config file path
        config_path = self._get_config_path(config_name)

        # Check if config file exists
        return os.path.exists(config_path)

    def load_configuration(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """Load tool configuration and model settings from a file.

        Args:
            config_name: Optional name of the config to load (defaults to 'default')

        Returns:
            Dict containing the configuration settings
        """
        # Default to 'default' if no config name provided
        if not config_name:
            config_name = "default"

        # Sanitize filename
        config_name = self._sanitize_config_name(config_name)

        # Create config file path
        config_path = self._get_config_path(config_name)

        # Check if config file exists
        if not os.path.exists(config_path):
            self.console.print(Panel(
                f"[yellow]Configuration file not found:[/yellow]\n"
                f"[blue]{config_path}[/blue]",
                title="Config Not Found", border_style="yellow", expand=False
            ))
            return default_config()

        # Read config file
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Validate loaded configuration and provide defaults for missing fields
            validated_config = self._validate_config(config_data)
            return validated_config

        except Exception as e:
            self.console.print(Panel(
                f"[red]Error loading configuration:[/red]\n"
                f"{str(e)}",
                title="Error", border_style="red", expand=False
            ))
            return default_config()

    def save_configuration(self, config_data: Dict[str, Any], config_name: Optional[str] = None) -> bool:
        """Save tool configuration and model settings to a file.

        Args:
            config_data: Dictionary containing the configuration to save
            config_name: Optional name for the config (defaults to 'default')

        Returns:
            bool: True if saved successfully, False otherwise
        """
        # Create config directory if it doesn't exist
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)

        # Default to 'default' if no config name provided
        if not config_name:
            config_name = "default"

        # Sanitize filename
        config_name = self._sanitize_config_name(config_name)

        # Create config file path
        config_path = self._get_config_path(config_name)

        # Write to file
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.console.print(Panel(
                f"[green]Configuration saved successfully to:[/green]\n"
                f"[blue]{config_path}[/blue]",
                title="Config Saved", border_style="green", expand=False
            ))
            return True

        except Exception as e:
            self.console.print(Panel(
                f"[red]Error saving configuration:[/red]\n"
                f"{str(e)}",
                title="Error", border_style="red", expand=False
            ))
            return False

    def reset_configuration(self) -> Dict[str, Any]:
        """Reset tool configuration to default (all tools enabled).

        Returns:
            Dict containing the default configuration
        """
        config = default_config()

        self.console.print(Panel(
            "[green]Configuration reset to defaults![/green]\n"
            "• All tools enabled\n"
            "• Context retention enabled\n"
            "• Thinking mode enabled\n"
            "• Thinking text hidden",
            title="Config Reset", border_style="green", expand=False
        ))

        return config

    def _sanitize_config_name(self, config_name: str) -> str:
        """Sanitize configuration name for use in filenames.

        Args:
            config_name: Name to sanitize

        Returns:
            str: Sanitized name safe for use in filenames
        """
        sanitized = ''.join(c for c in config_name if c.isalnum() or c in ['-', '_']).lower()
        return sanitized or "default"

    def _get_config_path(self, config_name: str) -> str:
        """Get the full path to a configuration file.

        Args:
            config_name: Name of the configuration

        Returns:
            str: Full path to the configuration file
        """
        if config_name == "default":
            return os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
        else:
            return os.path.join(DEFAULT_CONFIG_DIR, f"{config_name}.json")

    def _validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration data and provide defaults for missing fields.

        Args:
            config_data: Configuration data to validate

        Returns:
            Dict: Validated configuration with defaults applied where needed
        """
        # Start with default configuration
        validated = default_config()

        # Apply values from the loaded configuration if they exist
        if "model" in config_data:
            validated["model"] = config_data["model"]

        if "enabledTools" in config_data and isinstance(config_data["enabledTools"], dict):
            validated["enabledTools"] = config_data["enabledTools"]

        if "contextSettings" in config_data and isinstance(config_data["contextSettings"], dict):
            if "retainContext" in config_data["contextSettings"]:
                validated["contextSettings"]["retainContext"] = bool(config_data["contextSettings"]["retainContext"])

        if "modelSettings" in config_data and isinstance(config_data["modelSettings"], dict):
            if "thinkingMode" in config_data["modelSettings"]:
                validated["modelSettings"]["thinkingMode"] = bool(config_data["modelSettings"]["thinkingMode"])
            if "showThinking" in config_data["modelSettings"]:
                validated["modelSettings"]["showThinking"] = bool(config_data["modelSettings"]["showThinking"])

        if "modelConfig" in config_data and isinstance(config_data["modelConfig"], dict):
            model_config = config_data["modelConfig"]
            if "system_prompt" in model_config:
                validated["modelConfig"]["system_prompt"] = str(model_config["system_prompt"])
            if "num_keep" in model_config:
                validated["modelConfig"]["num_keep"] = model_config["num_keep"] if model_config["num_keep"] is not None else None
            if "seed" in model_config:
                validated["modelConfig"]["seed"] = model_config["seed"] if model_config["seed"] is not None else None
            if "num_predict" in model_config:
                validated["modelConfig"]["num_predict"] = model_config["num_predict"] if model_config["num_predict"] is not None else None
            if "top_k" in model_config:
                validated["modelConfig"]["top_k"] = model_config["top_k"] if model_config["top_k"] is not None else None
            if "top_p" in model_config:
                validated["modelConfig"]["top_p"] = model_config["top_p"] if model_config["top_p"] is not None else None
            if "min_p" in model_config:
                validated["modelConfig"]["min_p"] = model_config["min_p"] if model_config["min_p"] is not None else None
            if "typical_p" in model_config:
                validated["modelConfig"]["typical_p"] = model_config["typical_p"] if model_config["typical_p"] is not None else None
            if "repeat_last_n" in model_config:
                validated["modelConfig"]["repeat_last_n"] = model_config["repeat_last_n"] if model_config["repeat_last_n"] is not None else None
            if "temperature" in model_config:
                validated["modelConfig"]["temperature"] = model_config["temperature"] if model_config["temperature"] is not None else None
            if "repeat_penalty" in model_config:
                validated["modelConfig"]["repeat_penalty"] = model_config["repeat_penalty"] if model_config["repeat_penalty"] is not None else None
            if "presence_penalty" in model_config:
                validated["modelConfig"]["presence_penalty"] = model_config["presence_penalty"] if model_config["presence_penalty"] is not None else None
            if "frequency_penalty" in model_config:
                validated["modelConfig"]["frequency_penalty"] = model_config["frequency_penalty"] if model_config["frequency_penalty"] is not None else None
            if "stop" in model_config:
                validated["modelConfig"]["stop"] = model_config["stop"] if model_config["stop"] is not None else None
            if "num_ctx" in model_config:
                validated["modelConfig"]["num_ctx"] = model_config["num_ctx"] if model_config["num_ctx"] is not None else None
            if "num_batch" in model_config:
                validated["modelConfig"]["num_batch"] = model_config["num_batch"] if model_config["num_batch"] is not None else None


        if "displaySettings" in config_data and isinstance(config_data["displaySettings"], dict):
            if "showToolExecution" in config_data["displaySettings"]:
                validated["displaySettings"]["showToolExecution"] = bool(config_data["displaySettings"]["showToolExecution"])
            if "showMetrics" in config_data["displaySettings"]:
                validated["displaySettings"]["showMetrics"] = bool(config_data["displaySettings"]["showMetrics"])

        if "hilSettings" in config_data and isinstance(config_data["hilSettings"], dict):
            if "enabled" in config_data["hilSettings"]:
                validated["hilSettings"]["enabled"] = bool(config_data["hilSettings"]["enabled"])

        return validated
