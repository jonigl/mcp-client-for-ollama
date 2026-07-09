"""Sanitization helpers for displaying untrusted text in the terminal.

Tool arguments and tool responses can echo content supplied by a malicious MCP
server. Anything shown in the terminal must not be able to emit raw ANSI escape
sequences or other control characters, which could spoof the display or hide
part of the content from the user (e.g. cursor moves, screen clears, or the
"conceal" SGR code).
"""

import re

# Control characters that could corrupt or spoof a terminal (raw ANSI escapes,
# carriage returns, backspaces, C1 controls, DEL, ...). ESC (0x1b) lives in
# 0x0b-0x1f, so it is stripped here. Tab (0x09) and newline (0x0a) are kept:
# they render harmlessly and newline is needed for readable multi-line values.
#
# Note: Rich's own ``strip_control_codes`` is NOT sufficient — it leaves ESC
# untouched, so it would not neutralize ANSI escape sequences.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def strip_control_chars(text: str) -> str:
    """Remove terminal control characters (keeping tab and newline).

    This neutralizes ANSI escape sequences and other control characters so an
    untrusted string can't spoof the terminal or hide part of its content when
    printed. The text is otherwise left intact, never truncated.
    """
    return _CONTROL_CHARS.sub("", text)
