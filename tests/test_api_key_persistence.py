"""Tests for API key persistence in MCPClient.save_configuration().

Keys supplied through the OLLMCP_API_KEY env var (persist_api_key=False) must
never be written to the config file, while keys passed via --api-key
(persist_api_key=True) are saved. A previously saved key is preserved when a
non-persistable key is in use.
"""

import json

from mcp_client_for_ollama.client import MCPClient
from mcp_client_for_ollama.config import manager as config_manager


def _saved_api_key(config_dir, provider="ollama"):
    with open(config_dir / "config.json") as f:
        return json.load(f)["providers"][provider]["apiKey"]


def _make_client():
    client = MCPClient()
    client.model_manager.set_model("test-model")
    return client


def test_flag_key_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "DEFAULT_CONFIG_DIR", str(tmp_path))
    client = _make_client()
    client.api_key = "sk-flag"
    client.persist_api_key = True

    client.save_configuration()

    assert _saved_api_key(tmp_path) == "sk-flag"


def test_env_key_is_not_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "DEFAULT_CONFIG_DIR", str(tmp_path))
    client = _make_client()
    client.api_key = "sk-env"
    client.persist_api_key = False

    client.save_configuration()

    assert _saved_api_key(tmp_path) == ""


def test_env_key_preserves_previously_saved_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "DEFAULT_CONFIG_DIR", str(tmp_path))

    # First run saves a key from the --api-key flag.
    client = _make_client()
    client.api_key = "sk-saved"
    client.persist_api_key = True
    client.save_configuration()

    # A later run uses an env-var key, which must not overwrite the saved one.
    client.api_key = "sk-env"
    client.persist_api_key = False
    client.save_configuration()

    assert _saved_api_key(tmp_path) == "sk-saved"
