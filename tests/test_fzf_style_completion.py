"""Tests for slash-namespace completion behavior."""

import unittest

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


if __name__ == "__main__":
    unittest.main()
