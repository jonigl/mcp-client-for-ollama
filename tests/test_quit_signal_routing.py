"""Tests for Ctrl+C/Ctrl+D routing to slash quit behavior."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from prompt_toolkit.history import InMemoryHistory

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

    async def test_single_line_mode_uses_single_line_prompt(self):
        client = MCPClient.__new__(MCPClient)
        client.prompt_session = MagicMock()
        client.prompt_session.prompt_async = AsyncMock(return_value="hello")
        client.input_mode = "single"

        user_input = await MCPClient.get_user_input(client, prompt_text="test")

        self.assertEqual(user_input, "hello")
        call = client.prompt_session.prompt_async.await_args
        self.assertEqual(call.args[0], "test❯ ")
        self.assertFalse(call.kwargs["multiline"])
        self.assertNotIn("key_bindings", call.kwargs)
        self.assertNotIn("bottom_toolbar", call.kwargs)
        self.assertNotIn("prompt_continuation", call.kwargs)
        self.assertIsNone(client.prompt_session.key_bindings)
        self.assertIsNone(client.prompt_session.bottom_toolbar)
        self.assertIsNone(client.prompt_session.prompt_continuation)

    async def test_multiline_mode_enables_toolbar_and_key_bindings(self):
        client = MCPClient.__new__(MCPClient)
        client.prompt_session = MagicMock()
        client.prompt_session.prompt_async = AsyncMock(return_value="line one\nline two")
        client.input_mode = "multiline"

        user_input = await MCPClient.get_user_input(client, prompt_text="test")

        self.assertEqual(user_input, "line one\nline two")
        call = client.prompt_session.prompt_async.await_args
        self.assertEqual(call.args[0], "test❯ ")
        self.assertTrue(call.kwargs["multiline"])
        self.assertIn("key_bindings", call.kwargs)
        self.assertIn("bottom_toolbar", call.kwargs)
        self.assertIn("prompt_continuation", call.kwargs)
        self.assertTrue(call.kwargs["bottom_toolbar"])
        toolbar_fragments = call.kwargs["bottom_toolbar"]()
        toolbar_text = "".join(fragment[1] for fragment in toolbar_fragments)
        self.assertIn("Esc then Enter", toolbar_text)
        self.assertEqual(call.kwargs["prompt_continuation"](20, 1, 0), "")

    async def test_switching_multiline_to_singleline_clears_toolbar_and_bindings(self):
        client = MCPClient.__new__(MCPClient)
        client.prompt_session = MagicMock()
        client.prompt_session.prompt_async = AsyncMock(side_effect=["line one\nline two", "hello"])

        client.input_mode = "multiline"
        multiline_value = await MCPClient.get_user_input(client, prompt_text="test")

        client.input_mode = "single"
        single_value = await MCPClient.get_user_input(client, prompt_text="test")

        self.assertEqual(multiline_value, "line one\nline two")
        self.assertEqual(single_value, "hello")

        first_call = client.prompt_session.prompt_async.await_args_list[0]
        self.assertTrue(first_call.kwargs["multiline"])
        self.assertIsNotNone(first_call.kwargs["key_bindings"])
        self.assertIsNotNone(first_call.kwargs["bottom_toolbar"])
        self.assertIsNotNone(first_call.kwargs["prompt_continuation"])

        second_call = client.prompt_session.prompt_async.await_args_list[1]
        self.assertFalse(second_call.kwargs["multiline"])
        self.assertNotIn("key_bindings", second_call.kwargs)
        self.assertNotIn("bottom_toolbar", second_call.kwargs)
        self.assertNotIn("prompt_continuation", second_call.kwargs)
        self.assertIsNone(client.prompt_session.key_bindings)
        self.assertIsNone(client.prompt_session.bottom_toolbar)
        self.assertIsNone(client.prompt_session.prompt_continuation)

    async def test_select_input_mode_preserves_shared_input_history(self):
        client = MCPClient.__new__(MCPClient)
        client.chat_input_history = InMemoryHistory()
        client.prompt_manager = None
        client.console = MagicMock()
        original_completer = MagicMock()
        client.prompt_session = MagicMock()
        client.prompt_session.completer = original_completer
        client.input_mode = "single"

        with patch(
            "mcp_client_for_ollama.client.get_input_no_autocomplete",
            new=AsyncMock(return_value="multiline"),
        ):
            await MCPClient.select_input_mode(client)

        self.assertEqual(client.input_mode, "multiline")
        self.assertIs(client.prompt_session.history, client.chat_input_history)
        self.assertIs(client.prompt_session.completer, original_completer)

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
