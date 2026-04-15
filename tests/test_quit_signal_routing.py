"""Tests for Ctrl+C/Ctrl+D routing to slash quit behavior."""

import unittest
from unittest.mock import AsyncMock, MagicMock

from mcp_client_for_ollama.client import MCPClient
from mcp_client_for_ollama.prompts.commands import run_slash_command
from mcp_client_for_ollama.prompts.routing import parse_user_input


class TestQuitSignalRouting(unittest.IsolatedAsyncioTestCase):
    """Validate interrupt/end-of-input signals route to slash quit."""

    async def test_keyboard_interrupt_maps_to_slash_quit(self):
        client = MCPClient.__new__(MCPClient)
        client.prompt_session = MagicMock()
        client.prompt_session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt)

        user_input = await MCPClient.get_user_input(client, prompt_text="test")

        self.assertEqual(user_input, "/quit")

    async def test_eof_maps_to_slash_quit(self):
        client = MCPClient.__new__(MCPClient)
        client.prompt_session = MagicMock()
        client.prompt_session.prompt_async = AsyncMock(side_effect=EOFError)

        user_input = await MCPClient.get_user_input(client, prompt_text="test")

        self.assertEqual(user_input, "/quit")

    def test_parse_slash_quit_input_is_command(self):
        intent, value = parse_user_input("/quit")

        self.assertEqual(intent, "slash-command")
        self.assertEqual(value, "quit")

    async def test_slash_quit_command_exits_loop(self):
        client = MagicMock()
        client.console = MagicMock()

        should_continue = await run_slash_command(client, "quit")

        self.assertFalse(should_continue)


if __name__ == "__main__":
    unittest.main()
