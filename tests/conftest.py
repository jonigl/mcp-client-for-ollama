"""Shared fixtures for the test suite."""

import pytest

from mcp_client_for_ollama.utils import server_logs


@pytest.fixture(autouse=True)
def isolate_server_logs(tmp_path_factory, monkeypatch):
    """Keep server log files out of the user's real ~/.config/ollmcp/logs.

    Any test that opens a connection builds a ServerLogSink, which creates its
    session directory and prunes the older ones. Without this, running the
    suite writes into the user's log directory and deletes the logs of their
    past ollmcp sessions.
    """
    monkeypatch.setattr(server_logs, "SERVER_LOG_DIR", str(tmp_path_factory.mktemp("logs")))
