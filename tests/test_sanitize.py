"""Tests for terminal-output sanitization.

Covers the shared ``strip_control_chars`` primitive and its use in the tool
response panel, which is shown regardless of the HIL setting and renders
content coming straight from the (untrusted) MCP server.
"""

import io
import re
import unittest

from rich.console import Console

from mcp_client_for_ollama.utils.sanitize import strip_control_chars
from mcp_client_for_ollama.utils.tool_display import ToolDisplayManager


class TestStripControlChars(unittest.TestCase):
    def test_strips_ansi_escape_sequences(self):
        # ESC (0x1b) must be removed so the sequence renders as inert text.
        evil = "Hello\x1b[2J\x1b[31mred\x1b[8mhidden"
        assert strip_control_chars(evil) == "Hello[2J[31mred[8mhidden"
        assert "\x1b" not in strip_control_chars(evil)

    def test_strips_c1_and_del_and_other_controls(self):
        assert strip_control_chars("a\x07\x08\x0d\x7f\x9bb") == "ab"

    def test_keeps_tab_and_newline(self):
        assert strip_control_chars("a\tb\nc") == "a\tb\nc"

    def test_leaves_plain_text_untouched(self):
        text = "normal text with [brackets] and 日本語"
        assert strip_control_chars(text) == text


class TestToolResponseSanitization(unittest.TestCase):
    def _render_response(self, tool_response):
        """Render display_tool_response into a captured terminal buffer."""
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=80,
                          color_system="standard")
        ToolDisplayManager(console).display_tool_response(
            "evil_tool", {"q": "x"}, tool_response, show=True)
        return buf.getvalue()

    def test_plain_text_response_cannot_inject_ansi(self):
        # Non-JSON, few markdown patterns -> plain Text branch.
        out = self._render_response("done\x1b[2J\x1b[8m secret\x1b[0m")
        assert "\x1b[2J" not in out
        assert "\x1b[8m" not in out
        assert "[2J" in out  # neutralized escape shows as literal text

    def test_markdown_response_cannot_inject_ansi(self):
        # Enough markdown patterns (>7) -> Markdown branch.
        payload = ("# Title\n- **a**\n- *b*\n- `c`\n> quote\n"
                   "[l](u) more\x1b[2J\x1b[8mhidden")
        out = self._render_response(payload)
        assert "\x1b[2J" not in out
        assert "\x1b[8m" not in out

    def test_json_response_content_still_shown(self):
        # The JSON path is unaffected by stripping (valid JSON has no raw
        # control bytes); its content must still render.
        out = self._render_response('{"result": "ok_marker"}')
        assert "ok_marker" in out


class TestNoWidthTruncation(unittest.TestCase):
    """Long JSON values must wrap, not be cropped off the panel (word_wrap)."""

    def _visible(self, fn_name, *args, width=100):
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=width,
                          color_system="standard")
        getattr(ToolDisplayManager(console), fn_name)(*args)
        # Strip SGR codes so we compare the visible characters only.
        return re.sub(r"\x1b\[[0-9;:]*m", "", buf.getvalue())

    def test_long_argument_value_not_cropped(self):
        long_value = "START_" + "A" * 140 + "_END"
        out = self._visible("display_tool_execution", "shell",
                            {"command": long_value})
        assert "_END" in out

    def test_long_json_response_value_not_cropped(self):
        long_value = "START_" + "A" * 140 + "_END"
        out = self._visible("display_tool_response", "shell", {"q": "x"},
                            '{"stdout": "%s"}' % long_value)
        assert "_END" in out


if __name__ == "__main__":
    unittest.main()
