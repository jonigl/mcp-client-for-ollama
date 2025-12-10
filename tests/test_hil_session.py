import unittest
from unittest.mock import MagicMock, patch
from mcp_client_for_ollama.utils.hil_manager import HumanInTheLoopManager, AbortQueryException

class TestHumanInTheLoopManagerSession(unittest.IsolatedAsyncioTestCase):
    def test_session_auto_execute_initially_false(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)
        assert manager._session_auto_execute is False

    def test_set_session_auto_execute(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)
        manager.set_session_auto_execute(True)
        assert manager._session_auto_execute is True
        manager.set_session_auto_execute(False)
        assert manager._session_auto_execute is False

    def test_reset_session(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)
        manager.set_session_auto_execute(True)
        manager.reset_session()
        assert manager._session_auto_execute is False

    async def test_request_tool_confirmation_session_enabled(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)
        manager.set_session_auto_execute(True)

        # Should return True without prompting
        result = await manager.request_tool_confirmation("test_tool", {})
        assert result is True

    async def test_request_tool_confirmation_hil_disabled(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)
        manager.set_enabled(False)

        result = await manager.request_tool_confirmation("test_tool", {})
        assert result is True

    def test_handle_user_choice_session(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)

        with patch('rich.prompt.Prompt.ask', return_value='y'):
            result = manager._handle_user_choice('session')

        assert result is True
        assert manager._session_auto_execute is True

    def test_handle_user_choice_abort_raises_exception(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)

        with self.assertRaises(AbortQueryException) as context:
            manager._handle_user_choice('abort')

        assert "Query aborted by user" in str(context.exception)

    def test_handle_user_choice_abort_shorthand(self):
        console_mock = MagicMock()
        manager = HumanInTheLoopManager(console_mock)

        with self.assertRaises(AbortQueryException):
            manager._handle_user_choice('a')
