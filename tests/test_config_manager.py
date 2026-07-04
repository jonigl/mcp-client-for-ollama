"""Tests for configuration manager. Copyright 2026 ITTH GmbH & Co. KG"""

from mcp_client_for_ollama.config.manager import ConfigManager
from mcp_client_for_ollama.config.defaults import default_config
from rich.console import Console


def test_validate_config_preserves_providers_map():
    """A new-format config keeps its per-provider profiles and defaultProvider."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "defaultProvider": "openai",
        "providers": {
            "ollama": {"host": "http://localhost:11434", "model": "qwen3:0.6b", "apiKey": ""},
            "openai": {"host": "", "model": "gpt-4o", "apiKey": "sk-test"},
        },
    })

    assert validated["defaultProvider"] == "openai"
    assert validated["providers"]["openai"] == {"host": "", "model": "gpt-4o", "apiKey": "sk-test"}
    assert validated["providers"]["ollama"]["model"] == "qwen3:0.6b"


def test_validate_config_migrates_legacy_flat_config():
    """A legacy flat config is migrated into a single provider profile."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "host": "https://api.atlascloud.ai/v1",
        "model": "deepseek",
        "provider": "openai",
        "apiKey": "sk-legacy",
    })

    assert validated["defaultProvider"] == "openai"
    assert validated["providers"]["openai"] == {
        "host": "https://api.atlascloud.ai/v1",
        "model": "deepseek",
        "apiKey": "sk-legacy",
    }


def test_validate_config_legacy_without_provider_defaults_to_ollama():
    """A legacy config lacking a provider migrates under ollama."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({"model": "test-model"})

    assert validated["defaultProvider"] == "ollama"
    assert validated["providers"]["ollama"]["model"] == "test-model"


def test_validate_config_seeds_default_provider_when_absent():
    """A config with neither providers nor connection fields still seeds ollama."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({"displaySettings": {"answerRenderMode": "both"}})

    assert validated["defaultProvider"] == "ollama"
    assert "ollama" in validated["providers"]


def test_save_load_round_trip_preserves_all_providers(monkeypatch, tmp_path):
    """Saving and reloading keeps every provider profile and the default."""
    import mcp_client_for_ollama.config.manager as manager_module

    monkeypatch.setattr(manager_module, "DEFAULT_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(manager_module, "DEFAULT_CONFIG_FILE", "config.json")

    mgr = ConfigManager(Console())
    cfg = default_config()
    cfg["providers"]["openai"] = {"host": "", "model": "gpt-4o", "apiKey": "sk-test"}
    cfg["defaultProvider"] = "openai"

    assert mgr.save_configuration(cfg, "default") is True

    loaded = mgr.load_configuration("default")
    assert loaded["defaultProvider"] == "openai"
    assert loaded["providers"]["openai"]["model"] == "gpt-4o"
    assert loaded["providers"]["openai"]["apiKey"] == "sk-test"
    # The pre-existing ollama profile is not dropped.
    assert "ollama" in loaded["providers"]


def test_default_config_shows_thinking_text():
    """Test that thinking text is visible by default in new configurations."""
    config = default_config()

    assert config["modelSettings"]["showThinking"] is True


def test_default_config_uses_both_answer_render_modes():
    """Test that new configurations keep the current dual answer display behavior."""
    config = default_config()

    assert config["displaySettings"]["answerRenderMode"] == "markdown"


def test_validate_config_preserves_answer_render_mode():
    """Test that a valid answer render mode survives configuration validation."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "displaySettings": {
            "answerRenderMode": "both"
        }
    })

    assert validated["displaySettings"]["answerRenderMode"] == "both"


def test_default_config_uses_single_line_input_mode():
    """Test that new configurations default to single-line chat input."""
    config = default_config()

    assert config["inputSettings"]["inputMode"] == "single"


def test_validate_config_preserves_input_mode():
    """Test that a valid input mode survives configuration validation."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "inputSettings": {
            "inputMode": "multiline"
        }
    })

    assert validated["inputSettings"]["inputMode"] == "multiline"


def test_validate_config_ignores_invalid_input_mode():
    """Test that invalid input modes fall back to defaults."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "inputSettings": {
            "inputMode": "invalid"
        }
    })

    assert validated["inputSettings"]["inputMode"] == "single"


def test_default_config_has_reasoning_effort():
    """New configurations include reasoningEffort = 'medium'."""
    config = default_config()

    assert config["modelSettings"]["reasoningEffort"] == "medium"


def test_validate_config_preserves_valid_reasoning_effort():
    """A valid reasoning effort level survives configuration validation."""
    mgr = ConfigManager(Console())

    for level in ("auto", "minimal", "low", "medium", "high", "xhigh"):
        validated = mgr._validate_config({
            "modelSettings": {"reasoningEffort": level}
        })
        assert validated["modelSettings"]["reasoningEffort"] == level


def test_validate_config_ignores_invalid_reasoning_effort():
    """An invalid reasoning effort falls back to the default 'medium'."""
    mgr = ConfigManager(Console())

    validated = mgr._validate_config({
        "modelSettings": {"reasoningEffort": "turbo-max-extreme"}
    })

    assert validated["modelSettings"]["reasoningEffort"] == "medium"
