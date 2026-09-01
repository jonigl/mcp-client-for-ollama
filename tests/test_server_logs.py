"""Test the log files MCP servers write to, and what of it reaches the screen."""

import asyncio
import io
import os
import sys
from contextlib import AsyncExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import LoggingCapability, ServerCapabilities
from rich.console import Console

from mcp_client_for_ollama.server import connector as connector_mod
from mcp_client_for_ollama.server.connector import ServerConnector
from mcp_client_for_ollama.utils import server_logs
from mcp_client_for_ollama.utils.server_logs import ServerLogSink, server_log_path


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Keep log files out of the real ~/.config/ollmcp/logs."""
    monkeypatch.setattr(server_logs, "SERVER_LOG_DIR", str(tmp_path))
    return tmp_path / server_logs._SESSION_DIR_NAME


def test_sink_writes_to_its_own_file(log_dir):
    sink = ServerLogSink("weather")

    assert sink.stream is not sys.stderr
    sink.stream.write("starting up\n")
    sink.close()

    assert (log_dir / "weather.log").read_text() == "starting up\n"


def test_sink_stays_silent_without_a_console(log_dir, capsys):
    sink = ServerLogSink("weather")
    sink.stream.write("noisy line\n")
    sink.close()

    captured = capsys.readouterr()
    assert "noisy line" not in captured.out
    assert "noisy line" not in captured.err


def test_sink_echoes_to_the_console_when_given_one(log_dir):
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=200)

    sink = ServerLogSink("weather", console=console, echo_stderr=True)
    sink.stream.write("extension connection ready\n")
    sink.close()

    assert "[weather] extension connection ready" in output.getvalue()
    assert (log_dir / "weather.log").read_text() == "extension connection ready\n"


def test_sink_sanitizes_echoed_lines(log_dir):
    """Server output is untrusted: it must not be able to emit raw escapes."""
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=200)

    sink = ServerLogSink("weather", console=console, echo_stderr=True)
    sink.stream.write("safe\x1b[2Jcleared\n")
    sink.close()

    echoed = output.getvalue()
    # The ESC is gone, so what is left is inert text rather than a screen clear
    assert "\x1b" not in echoed
    assert "[2J" in echoed
    # The log file keeps the raw bytes; only the terminal echo is sanitized
    assert "\x1b[2J" in (log_dir / "weather.log").read_text()


def test_each_session_gets_its_own_directory(log_dir):
    """Several ollmcp windows must not write over each other's files."""
    ServerLogSink("weather").close()

    assert log_dir.name.endswith(f"-{os.getpid()}")
    assert (log_dir / "weather.log").exists()


def test_reconnecting_keeps_what_the_server_already_logged(log_dir):
    first = ServerLogSink("weather")
    first.stream.write("before the reload\n")
    first.close()

    second = ServerLogSink("weather")
    second.stream.write("after the reload\n")
    second.close()

    assert (log_dir / "weather.log").read_text() == "before the reload\nafter the reload\n"


def test_prune_keeps_the_newest_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(server_logs, "SERVER_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(server_logs, "_is_running", lambda pid: False)
    for name in ["20260101-100000-11", "20260102-100000-22", "20260103-100000-33", "not-a-session"]:
        (tmp_path / name).mkdir()

    server_logs.prune_old_sessions(keep=2)

    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260102-100000-22", "20260103-100000-33", "not-a-session",
    ]


def test_prune_leaves_running_sessions_alone(tmp_path, monkeypatch):
    """With more windows open than we keep, the oldest is still a live session."""
    monkeypatch.setattr(server_logs, "SERVER_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(server_logs, "_is_running", lambda pid: pid == 11)
    for name in ["20260101-100000-11", "20260102-100000-22", "20260103-100000-33"]:
        (tmp_path / name).mkdir()

    server_logs.prune_old_sessions(keep=1)

    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260101-100000-11", "20260103-100000-33",
    ]


def test_sink_degrades_when_the_log_file_cannot_be_opened(tmp_path, monkeypatch):
    """A log file we cannot write is not a reason to refuse the connection."""
    blocker = tmp_path / "logs"
    blocker.write_text("not a directory")
    monkeypatch.setattr(server_logs, "SERVER_LOG_DIR", str(blocker))
    output = io.StringIO()

    sink = ServerLogSink("weather", console=Console(file=output, width=200))
    sink.log("still running")
    sink.close()

    assert sink.path is None
    assert "could not open the log file for weather" in output.getvalue()


def test_server_log_path_makes_the_name_filename_safe(log_dir):
    assert server_log_path("../../etc/passwd") == str(log_dir / "etc_passwd.log")
    assert server_log_path("my server") == str(log_dir / "my_server.log")
    assert server_log_path("...") == str(log_dir / "server.log")


def test_connector_passes_a_log_file_as_errlog(log_dir, monkeypatch):
    """The stdio transport must never be handed the client's own stderr."""
    captured = {}

    def fake_stdio_client(server_params, errlog=sys.stderr):
        captured["errlog"] = errlog
        raise RuntimeError("stop here, the transport is not what is under test")

    monkeypatch.setattr(connector_mod, "stdio_client", fake_stdio_client)

    async def run():
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack, console=Console(file=io.StringIO()))
            return await connector._connect_to_server(
                {"name": "weather", "type": "config", "config": {"command": sys.executable, "args": ["-c", "pass"]}}
            )

    assert asyncio.run(run()) is False
    assert captured["errlog"] is not sys.stderr
    assert captured["errlog"].name == str(log_dir / "weather.log")


def make_notification(level, data, logger=None):
    return SimpleNamespace(level=level, logger=logger, data=data)


def test_log_notifications_are_recorded_and_shown_from_the_wanted_level(log_dir):
    output = io.StringIO()
    connector = ServerConnector(AsyncExitStack(), console=Console(file=output, width=200), log_level="warning")
    sink = ServerLogSink("weather", console=connector.console)
    handle = connector._make_logging_callback(sink)

    asyncio.run(handle(make_notification("error", "upstream API is down")))
    asyncio.run(handle(make_notification("debug", "cache hit", logger="fetch")))
    sink.close()

    echoed = output.getvalue()
    assert "upstream API is down" in echoed
    assert "cache hit" not in echoed
    # Both are kept on disk regardless of what made it to the screen
    assert (log_dir / "weather.log").read_text() == (
        "error: upstream API is down\ndebug fetch: cache hit\n"
    )


def test_log_notifications_stay_off_screen_without_a_level(log_dir):
    output = io.StringIO()
    connector = ServerConnector(AsyncExitStack(), console=Console(file=output, width=200))
    sink = ServerLogSink("weather", console=connector.console)

    asyncio.run(connector._make_logging_callback(sink)(make_notification("emergency", "everything is on fire")))
    sink.close()

    assert output.getvalue() == ""
    assert "everything is on fire" in (log_dir / "weather.log").read_text()


def test_log_notifications_keep_their_raw_bytes_on_disk(log_dir):
    """Same rule as stderr: the file is raw, only the terminal echo is sanitized."""
    output = io.StringIO()
    connector = ServerConnector(AsyncExitStack(), console=Console(file=output, width=200), log_level="debug")
    sink = ServerLogSink("weather", console=connector.console)

    asyncio.run(connector._make_logging_callback(sink)(make_notification("error", "safe\x1b[2Jcleared")))
    sink.close()

    assert "\x1b" not in output.getvalue()
    assert "\x1b[2J" in (log_dir / "weather.log").read_text()


def test_debug_shows_every_level(log_dir):
    connector = ServerConnector(AsyncExitStack(), console=Console(file=io.StringIO()), debug=True)

    assert connector.log_level == "debug"
    assert connector._shows_level("debug") is True
    # A level outside the spec is shown rather than swallowed
    assert connector._shows_level("chatty") is True


def test_an_explicit_log_level_wins_over_debug(log_dir):
    """--debug --log-level error means stderr in full, notifications only from error."""
    connector = ServerConnector(
        AsyncExitStack(), console=Console(file=io.StringIO()), debug=True, log_level="error"
    )

    assert connector.log_level == "error"
    assert connector._shows_level("warning") is False
    assert connector._shows_level("error") is True


def test_log_level_is_set_on_servers_that_support_it():
    session = MagicMock()
    session.set_logging_level = AsyncMock()
    connector = ServerConnector(AsyncExitStack(), console=Console(file=io.StringIO()), log_level="warning")

    asyncio.run(connector._apply_log_level(session, "weather", ServerCapabilities(logging=LoggingCapability())))
    session.set_logging_level.assert_awaited_once_with("warning")

    session.set_logging_level.reset_mock()
    asyncio.run(connector._apply_log_level(session, "weather", ServerCapabilities()))
    session.set_logging_level.assert_not_awaited()


def test_log_level_is_not_set_when_none_was_asked_for():
    session = MagicMock()
    session.set_logging_level = AsyncMock()
    connector = ServerConnector(AsyncExitStack(), console=Console(file=io.StringIO()))

    asyncio.run(connector._apply_log_level(session, "weather", ServerCapabilities(logging=LoggingCapability())))

    session.set_logging_level.assert_not_awaited()
