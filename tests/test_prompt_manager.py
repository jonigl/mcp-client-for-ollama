"""Tests for prompt reference resolution behavior."""

import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock

from mcp_client_for_ollama.prompts.manager import PromptManager


@dataclass
class DummyPrompt:
    name: str
    description: str = ""
    arguments: list = None

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


class TestPromptManagerResolution(unittest.TestCase):
    """Validate qualified and unqualified prompt reference resolution."""

    def setUp(self):
        self.manager = PromptManager(console=MagicMock())
        self.manager.set_prompts(
            {
                "alpha": [DummyPrompt("summarize"), DummyPrompt("review")],
                "beta": [DummyPrompt("summarize"), DummyPrompt("draft")],
            }
        )

    def test_resolve_qualified_prompt(self):
        result = self.manager.resolve_prompt_reference("alpha:review")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["server_name"], "alpha")
        self.assertEqual(result["prompt"].name, "review")

    def test_resolve_unqualified_unique_prompt(self):
        result = self.manager.resolve_prompt_reference("draft")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["server_name"], "beta")
        self.assertEqual(result["prompt"].name, "draft")

    def test_resolve_unqualified_ambiguous_prompt(self):
        result = self.manager.resolve_prompt_reference("summarize")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["candidates"], ["alpha:summarize", "beta:summarize"])

    def test_resolve_missing_qualified_prompt(self):
        result = self.manager.resolve_prompt_reference("alpha:unknown")
        self.assertEqual(result["status"], "not-found")
        self.assertTrue(result["qualified"])
        self.assertEqual(result["server_name"], "alpha")
        self.assertEqual(result["prompt_name"], "unknown")
        self.assertTrue(result["server_exists"])

    def test_resolve_missing_qualified_server(self):
        result = self.manager.resolve_prompt_reference("gamma:unknown")
        self.assertEqual(result["status"], "not-found")
        self.assertTrue(result["qualified"])
        self.assertEqual(result["server_name"], "gamma")
        self.assertFalse(result["server_exists"])

    def test_resolve_missing_unqualified_prompt(self):
        result = self.manager.resolve_prompt_reference("unknown")
        self.assertEqual(result["status"], "not-found")
        self.assertFalse(result["qualified"])

    def test_resolve_invalid_reference(self):
        result = self.manager.resolve_prompt_reference("alpha:")
        self.assertEqual(result["status"], "invalid")

    def test_get_prompt_names_for_server_returns_sorted_names(self):
        names = self.manager.get_prompt_names_for_server("alpha")
        self.assertEqual(names, ["review", "summarize"])


if __name__ == "__main__":
    unittest.main()
