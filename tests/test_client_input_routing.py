"""Tests for slash input routing behavior."""

import unittest

from mcp_client_for_ollama.prompts.routing import parse_user_input, resolve_slash_command


class TestClientInputRouting(unittest.TestCase):
    """Validate slash command/prompt/query intent classification."""

    def test_resolve_interactive_command_alias(self):
        self.assertEqual(resolve_slash_command(" q "), "quit")
        self.assertEqual(resolve_slash_command("mc"), "model-config")
        self.assertEqual(resolve_slash_command("ste"), "show-tool-execution")
        self.assertEqual(resolve_slash_command("im"), "input-mode")

    def test_resolve_interactive_command_unknown(self):
        self.assertIsNone(resolve_slash_command("not-a-command"))

    def test_classify_empty_input(self):
        intent, value = parse_user_input("   ")
        self.assertEqual(intent, "empty")
        self.assertIsNone(value)

    def test_classify_slash_prompt_input(self):
        intent, value = parse_user_input(" /fix ")
        self.assertEqual(intent, "slash-prompt")
        self.assertEqual(value, "fix")

    def test_classify_slash_command_input(self):
        intent, value = parse_user_input("/h")
        self.assertEqual(intent, "slash-command")
        self.assertEqual(value, "help")

    def test_slash_command_precedence_over_prompt_like_name(self):
        intent, value = parse_user_input("/help")
        self.assertEqual(intent, "slash-command")
        self.assertEqual(value, "help")

    def test_slash_noncommand_routes_to_prompt(self):
        intent, value = parse_user_input("/helpful")
        self.assertEqual(intent, "slash-prompt")
        self.assertEqual(value, "helpful")

    def test_classify_non_slash_command_as_query(self):
        intent, value = parse_user_input("help")
        self.assertEqual(intent, "query")
        self.assertEqual(value, "help")

    def test_classify_short_plain_query_is_allowed(self):
        intent, value = parse_user_input("hi there")
        self.assertEqual(intent, "query")
        self.assertEqual(value, "hi there")

    def test_classify_multiline_query_preserves_internal_newlines(self):
        intent, value = parse_user_input("  first line\nsecond line\nthird line  ")
        self.assertEqual(intent, "query")
        self.assertEqual(value, "first line\nsecond line\nthird line")

    def test_classify_multiline_slash_command_still_routes_as_command(self):
        intent, value = parse_user_input("\n/help\n")
        self.assertEqual(intent, "slash-command")
        self.assertEqual(value, "help")

    def test_classify_slash_empty(self):
        intent, value = parse_user_input("/")
        self.assertEqual(intent, "slash-empty")
        self.assertIsNone(value)

    def test_classify_reserved_resource_prefix(self):
        intent, value = parse_user_input("@resource")
        self.assertEqual(intent, "resource")
        self.assertEqual(value, "@resource")


if __name__ == "__main__":
    unittest.main()
