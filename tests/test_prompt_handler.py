"""Tests for prompt handler resolution and guidance UX."""

import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

from mcp_client_for_ollama.prompts.handler import PromptHandler
from mcp_client_for_ollama.prompts.manager import PromptManager


@dataclass
class DummyPrompt:
    name: str
    description: str = ""
    arguments: list = None

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


def _history_context_manager(_entries):
    @contextmanager
    def _ctx():
        yield

    return _ctx()


class TestPromptHandlerResolutionUX(unittest.IsolatedAsyncioTestCase):
    """Validate prompt resolution errors and ambiguity guidance paths."""

    async def test_ambiguous_prompt_shows_up_to_eight_qualified_suggestions(self):
        console = MagicMock()
        manager = PromptManager(console=console)
        manager.set_prompts({f"s{i}": [DummyPrompt("same")] for i in range(10)})
        handler = PromptHandler(console=console, prompt_manager=manager)

        result = await handler.invoke_prompt(
            "same",
            sessions={},
            process_query_fn=AsyncMock(),
            history_context_manager=_history_context_manager,
        )

        self.assertFalse(result)

        printed = [call.args[0] for call in console.print.call_args_list if call.args]
        self.assertTrue(any("exists on multiple servers" in line for line in printed))

        candidate_lines = [line for line in printed if isinstance(line, str) and line.startswith("  [cyan]/")]
        self.assertEqual(len(candidate_lines), 8)
        self.assertIn("  [cyan]/s0:same[/cyan]", candidate_lines)

    async def test_qualified_not_found_lists_server_specific_suggestions(self):
        console = MagicMock()
        manager = PromptManager(console=console)
        manager.set_prompts({"alpha": [DummyPrompt("draft"), DummyPrompt("summarize")]})
        handler = PromptHandler(console=console, prompt_manager=manager)

        result = await handler.invoke_prompt(
            "alpha:missing",
            sessions={},
            process_query_fn=AsyncMock(),
            history_context_manager=_history_context_manager,
        )

        self.assertFalse(result)

        printed = [call.args[0] for call in console.print.call_args_list if call.args]
        self.assertTrue(any("Prompt 'missing' not found on server 'alpha'." in line for line in printed))
        self.assertIn("  [cyan]/alpha:draft[/cyan]", printed)
        self.assertIn("  [cyan]/alpha:summarize[/cyan]", printed)

    async def test_qualified_not_found_reports_missing_server(self):
        console = MagicMock()
        manager = PromptManager(console=console)
        manager.set_prompts({"alpha": [DummyPrompt("draft")]})
        handler = PromptHandler(console=console, prompt_manager=manager)

        result = await handler.invoke_prompt(
            "beta:missing",
            sessions={},
            process_query_fn=AsyncMock(),
            history_context_manager=_history_context_manager,
        )

        self.assertFalse(result)

        printed = [call.args[0] for call in console.print.call_args_list if call.args]
        self.assertTrue(any("Server 'beta' was not found." in line for line in printed))


if __name__ == "__main__":
    unittest.main()
