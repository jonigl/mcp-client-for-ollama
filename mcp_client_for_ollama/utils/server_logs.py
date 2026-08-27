"""Per-server log files for what MCP servers report.

Servers report through two channels: a stdio server writes to stderr, and any
server can send MCP log notifications. Both end up in the server's log file
here; what reaches the screen is decided by the caller, since a stdio server
inherits the client's stderr unless given somewhere else to write and would
otherwise print over whatever ollmcp is rendering (issue #293).
"""

import os
import re
import shutil
import threading
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.markup import escape

from .constants import KEPT_LOG_SESSIONS, SERVER_LOG_DIR
from .sanitize import strip_control_chars

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")

# Log directory of one run: a timestamp for ordering plus the pid, which is what
# keeps several ollmcp windows from writing over each other's files.
_SESSION_DIR_NAME = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
_SESSION_DIR_PATTERN = re.compile(r"^\d{8}-\d{6}-(\d+)$")


def session_log_dir() -> str:
    """Directory holding the log files of this run."""
    return os.path.join(SERVER_LOG_DIR, _SESSION_DIR_NAME)


def server_log_path(server_name: str) -> str:
    """Path of a server's log file, with its name made filename-safe."""
    safe_name = _UNSAFE_FILENAME_CHARS.sub("_", server_name).strip("._") or "server"
    return os.path.join(session_log_dir(), f"{safe_name}.log")


def prune_old_sessions(keep: int = KEPT_LOG_SESSIONS) -> None:
    """Delete the log directories of previous runs, keeping the newest ones.

    Directories are named after the session's pid, and one whose process is
    still alive is never deleted: with more windows open than ``keep``, the
    oldest of them is a running session, not an old one.
    """
    try:
        entries = sorted(os.listdir(SERVER_LOG_DIR))
    except OSError:
        return

    sessions = [(name, int(m.group(1))) for name in entries if (m := _SESSION_DIR_PATTERN.match(name))]
    for name, pid in sessions[:-keep]:
        if _is_running(pid):
            continue
        shutil.rmtree(os.path.join(SERVER_LOG_DIR, name), ignore_errors=True)


def _is_running(pid: int) -> bool:
    """Whether a process is still alive."""
    if os.name == "nt":
        # os.kill() on Windows terminates the process instead of probing it.
        # Nothing is checked there: Windows refuses to delete files a live
        # session still has open, so its logs survive the prune anyway.
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        # Alive but not ours to signal
        return True
    return True


class ServerLogSink:
    """Log file of one server, fed by its stderr and its log notifications.

    ``stream`` is what gets handed to ``stdio_client(errlog=...)``. It has to be
    a real file object: the SDK passes it straight to ``anyio.open_process`` as
    the subprocess stderr, so an object that merely implements ``write()`` will
    not do.

    Without ``echo_stderr`` the sink is just the log file. With it, the server
    writes into a pipe that a reader thread drains into both the file and the
    console — a thread rather than an asyncio reader so it behaves the same on
    Windows, and draining is not optional: a pipe nobody reads fills up and
    blocks the server. Echoed lines are sanitized, since they are text from the
    server.
    """

    def __init__(self, server_name: str, console: Optional[Console] = None, echo_stderr: bool = False):
        self.server_name = server_name
        self.path = server_log_path(server_name)
        self._console = console
        self._lock = threading.Lock()
        self._reader = None
        self._pipe = None

        try:
            os.makedirs(session_log_dir(), exist_ok=True)
            prune_old_sessions()
            # Appended to, so reconnecting a server mid-session keeps what came before
            self._file = open(self.path, "a", encoding="utf-8", errors="replace")
        except OSError as e:
            # Nowhere to write (read-only home, no space, ...). Not having a log
            # file is not a reason to refuse the connection: the server still
            # connects, its output is just dropped. ``path`` is cleared so the
            # caller does not point the user at a file that was never written.
            if console is not None:
                console.print(
                    f"[yellow]Warning: could not open the log file for {server_name} "
                    f"({e}); its output will not be recorded[/yellow]"
                )
            self.path = None
            self._file = open(os.devnull, "w", encoding="utf-8")

        if not (echo_stderr and console is not None):
            self.stream = self._file
            return

        read_fd, write_fd = os.pipe()
        self.stream = os.fdopen(write_fd, "w", encoding="utf-8", errors="replace", buffering=1)
        self._pipe = os.fdopen(read_fd, "r", encoding="utf-8", errors="replace")
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def log(self, message: str, echo: bool = True) -> None:
        """Record a message the server sent over the MCP logging channel."""
        self._write(message + "\n")
        if echo:
            self._echo(message)

    def close(self) -> None:
        """Close the sink; the reader thread stops once the pipe reaches EOF."""
        try:
            self.stream.close()
        except OSError:
            pass
        if self._reader is not None:
            self._reader.join(timeout=2)
        if self._pipe is not None:
            self._pipe.close()
        if self._file is not self.stream:
            self._file.close()

    def _drain(self) -> None:
        for line in self._pipe:
            self._write(line)
            self._echo(line)

    def _write(self, text: str) -> None:
        with self._lock:
            self._file.write(text)
            self._file.flush()

    def _echo(self, text: str) -> None:
        """Print a line from the server, stripped of anything that could spoof
        the terminal."""
        if self._console is None:
            return
        clean = strip_control_chars(text).strip()
        if clean:
            self._console.print(f"[dim]\\[{escape(self.server_name)}] {escape(clean)}[/dim]")
