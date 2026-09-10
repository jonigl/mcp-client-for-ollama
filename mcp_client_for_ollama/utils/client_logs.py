"""Log file for what ollmcp itself reports.

The MCP servers' output goes to their own files next to this one (see
server_logs); this is the client's side of the same session directory, so a
warning ollmcp raises while talking to the provider is recorded somewhere
instead of printed over the TUI.
"""

import logging
import os
from typing import Optional

from .server_logs import prune_old_sessions, session_log_dir

# ollmcp's own logger: every module's logger propagates up to it. The
# NullHandler keeps Python's last-resort handler, which writes to stderr and
# would print over whatever is being rendered, from ever kicking in.
logger = logging.getLogger("mcp_client_for_ollama")
logger.addHandler(logging.NullHandler())

# Set once the file is actually open, so nothing points the user at a log that
# was never written.
_active_log_path: Optional[str] = None


def client_log_path() -> Optional[str]:
    """Path of the client's log file, or None if nothing is being recorded."""
    return _active_log_path


def start_client_log() -> None:
    """Send ollmcp's own log records to this run's log file.

    Called once at startup. Nowhere to write (read-only home, no space, ...) is
    not a reason to refuse to start: the records are simply dropped, same as
    what a server's sink does with its output.
    """
    global _active_log_path

    path = os.path.join(session_log_dir(), "ollmcp.log")
    try:
        os.makedirs(session_log_dir(), exist_ok=True)
        # This runs on every launch, including runs that never connect a server
        # and so never build a sink to prune from.
        prune_old_sessions()
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        return

    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    _active_log_path = path
