"""Tests for slash-namespace completion behavior."""

import unittest
from unittest.mock import patch

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from mcp_client_for_ollama.utils.fzf_style_completion import FZFStyleCompleter


class TestFZFStyleCompleter(unittest.TestCase):
    """Validate slash-only completion behavior for commands and prompts."""

    def setUp(self):
        self.completer = FZFStyleCompleter()
        self.completer.set_prompts(
            [
                {
                    "qualified_name": "alpha:summarize",
                    "name": "summarize",
                    "server": "alpha",
                    "description": "Summarize text",
                    "arguments": [],
                }
            ]
        )

    def _complete(self, text: str):
        document = Document(text=text, cursor_position=len(text))
        event = CompleteEvent(completion_requested=True)
        return list(self.completer.get_completions(document, event))

    def test_completes_slash_commands(self):
        completions = self._complete("/he")
        self.assertTrue(any(c.text == "help" for c in completions))

    def test_completes_qualified_prompts(self):
        completions = self._complete("/alpha:su")
        self.assertTrue(any(c.text == "alpha:summarize" for c in completions))

    def test_does_not_complete_plain_text_queries(self):
        completions = self._complete("he")
        self.assertEqual(completions, [])

    def test_command_meta_includes_shortcut_column(self):
        completions = self._complete("/clear")
        clear = next(c for c in completions if c.text == "clear")
        meta_texts = [text for _, text in clear.display_meta]
        self.assertTrue(any("/cc" in text for text in meta_texts))

    def test_alias_commands_show_canonical_shortcut(self):
        completions = self._complete("/exit")
        exit_cmd = next(c for c in completions if c.text == "exit")
        meta_texts = [text for _, text in exit_cmd.display_meta]
        self.assertTrue(any("/q" in text for text in meta_texts))

    def test_uses_tmux_badge_white_text(self):
        with patch.dict("os.environ", {"TMUX": "1"}, clear=False):
            completions = self._complete("/he")

        self.assertTrue(completions)
        # Index 1 is the badge; index 0 is the shortcut column
        badge_style = completions[0].display_meta[1][0]
        self.assertIn("bg:#ff8c00", badge_style)
        self.assertIn("fg:#ffffff", badge_style)


if __name__ == "__main__":
    unittest.main()
