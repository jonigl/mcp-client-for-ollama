"""Tests for slash command dispatch execution."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_client_for_ollama.prompts.commands import run_slash_command
from mcp_client_for_ollama.prompts.routing import SLASH_COMMAND_ALIASES
from mcp_client_for_ollama.utils.constants import INTERACTIVE_COMMANDS


class DummyClient:
    """Lightweight client double for slash command dispatch tests."""

    def __init__(self):
        self.console = MagicMock()
        self.select_tools = MagicMock()
        self.print_help = MagicMock()
        self.select_model = AsyncMock()
        self.configure_model_options = MagicMock()
        self.toggle_context_retention = MagicMock()
        self.toggle_thinking_mode = AsyncMock()
        self.toggle_show_thinking = AsyncMock()
        self.set_loop_limit = AsyncMock()
        self.toggle_show_tool_execution = MagicMock()
        self.toggle_show_metrics = MagicMock()
        self.select_answer_render_mode = AsyncMock()
        self.select_input_mode = AsyncMock()
        self.clear_context = MagicMock()
        self.display_context_stats = MagicMock()
        self.clear_console = MagicMock()
        self.display_available_tools = MagicMock()
        self.display_current_model = MagicMock()
        self.save_configuration = MagicMock()
        self.load_configuration = MagicMock()
        self.reset_configuration = MagicMock()
        self.reload_servers = AsyncMock()
        self.hil_manager = MagicMock()
        self.hil_manager.toggle = MagicMock()
        self.browse_prompts = MagicMock()
        self.chat_history = []


class TestSlashCommandExecution(unittest.IsolatedAsyncioTestCase):
    """Validate slash command dispatcher behavior and contract invariants."""

    async def test_run_quit_command_returns_false(self):
        client = DummyClient()

        result = await run_slash_command(client, "quit")

        self.assertFalse(result)
        client.console.print.assert_called_once()

    async def test_run_help_command_prints_help(self):
        client = DummyClient()

        result = await run_slash_command(client, "help")

        self.assertTrue(result)
        client.print_help.assert_called_once_with()

    async def test_run_model_command_awaits_selection(self):
        client = DummyClient()

        result = await run_slash_command(client, "model")

        self.assertTrue(result)
        client.select_model.assert_awaited_once_with()

    async def test_run_display_mode_command_awaits_selection(self):
        client = DummyClient()

        result = await run_slash_command(client, "display-mode")

        self.assertTrue(result)
        client.select_answer_render_mode.assert_awaited_once_with()

    async def test_run_input_mode_command_awaits_selection(self):
        client = DummyClient()

        result = await run_slash_command(client, "input-mode")

        self.assertTrue(result)
        client.select_input_mode.assert_awaited_once_with()

    async def test_run_import_history_replaces_chat_history(self):
        client = DummyClient()

        with patch(
            "mcp_client_for_ollama.prompts.commands.get_input_no_autocomplete",
            new=AsyncMock(return_value="/tmp/history.json"),
        ), patch(
            "mcp_client_for_ollama.prompts.commands.import_history",
            return_value=[{"query": "q", "response": "r"}],
        ):
            result = await run_slash_command(client, "import-history")

        self.assertTrue(result)
        self.assertEqual(client.chat_history, [{"query": "q", "response": "r"}])

    async def test_all_canonical_commands_are_handled(self):
        canonical_commands = set(SLASH_COMMAND_ALIASES.values())
        self.assertTrue(canonical_commands.issubset(set(INTERACTIVE_COMMANDS.keys())))

        with patch(
            "mcp_client_for_ollama.prompts.commands.get_input_no_autocomplete",
            new=AsyncMock(return_value=""),
        ), patch(
            "mcp_client_for_ollama.prompts.commands.display_full_history",
            return_value=None,
        ), patch(
            "mcp_client_for_ollama.prompts.commands.export_history",
            return_value=None,
        ), patch(
            "mcp_client_for_ollama.prompts.commands.import_history",
            return_value=None,
        ):
            for command_name in sorted(canonical_commands):
                client = DummyClient()
                result = await run_slash_command(client, command_name)
                if command_name == "quit":
                    self.assertFalse(result)
                else:
                    self.assertTrue(result)

    async def test_unknown_command_raises_assertion(self):
        client = DummyClient()

        with self.assertRaises(AssertionError):
            await run_slash_command(client, "not-a-command")


if __name__ == "__main__":
    unittest.main()
