"""
Input utilities for the MCP client for Ollama.

This module provides functions for getting user input without autocomplete
and reading a single keypress in a cross-platform manner.
"""

from __future__ import annotations

import os
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from .constants import DEFAULT_COMPLETION_STYLE


if os.name == "nt":
    import msvcrt

    def read_single_keypress() -> str:
        """
        Read a single keypress without requiring Enter.

        Uses the Windows console API via ``msvcrt``.
        Function keys and arrow keys emit a two-byte sequence; those
        prefixes are discarded so only meaningful key presses are returned.
        """
        while True:
            ch = msvcrt.getwch()

            # Function keys / arrow keys
            if ch in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue

            # Normalize Ctrl+C behaviour
            if ch == "\x03":
                raise KeyboardInterrupt

            return ch

else:
    import termios
    import tty

    def read_single_keypress() -> str:
        """
        Read a single keypress without requiring Enter.

        Uses POSIX terminal raw mode.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


async def get_input_no_autocomplete(prompt_text: str) -> str:
    """
    Prompt the user without autocomplete.

    Useful for file paths, configuration names and other free-form input.

    Args:
        prompt_text: Prompt displayed to the user.

    Returns:
        The user's input, or ``"quit"`` if the prompt is cancelled.
    """
    try:
        session = PromptSession(
            style=Style.from_dict(DEFAULT_COMPLETION_STYLE)
        )

        return await session.prompt_async(f"{prompt_text}❯ ")

    except (KeyboardInterrupt, EOFError):
        return "quit"
        