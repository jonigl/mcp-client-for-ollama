"""The request itself must show progress, not just the stream that follows it.

The streaming manager's spinner only starts once the response headers are in,
so the wait for the response used to leave the terminal blank. Against a cloud
provider that is seconds, and a request that never returns looks like a freeze
with nothing on screen to explain it.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from mcp_client_for_ollama.client import MCPClient


class RecordingStatus:
    """A console.status double that records whether it is currently showing."""

    def __init__(self, message):
        self.message = message
        self.active = False
        self.was_entered = False

    def __enter__(self):
        self.active = True
        self.was_entered = True
        return self

    def __exit__(self, *exc_info):
        self.active = False
        return False


class TestQueryProgress(unittest.IsolatedAsyncioTestCase):
    """A spinner covers the request, and is gone before the stream renders."""

    def setUp(self):
        self.client = MCPClient()
        self.statuses = []

        self.client.console = MagicMock()
        self.client.console.status.side_effect = self._make_status

        self.client.supports_thinking_mode = AsyncMock(return_value=False)
        self.client.supports_vision = AsyncMock(return_value=False)
        self.client.model_manager.get_current_model = MagicMock(return_value="a-model")
        self.client.tool_manager.get_enabled_tool_objects = MagicMock(return_value=[])

        self.status_active_during_request = None
        self.status_active_during_streaming = None

        self.client.llm.acompletion = AsyncMock(side_effect=self._record_request)
        self.client.streaming_manager.process_streaming_response = AsyncMock(
            side_effect=self._record_streaming
        )

    def _make_status(self, message, **kwargs):
        status = RecordingStatus(message)
        self.statuses.append(status)
        return status

    async def _record_request(self, *args, **kwargs):
        self.status_active_during_request = any(s.active for s in self.statuses)
        return MagicMock()

    async def _record_streaming(self, *args, **kwargs):
        self.status_active_during_streaming = any(s.active for s in self.statuses)
        return "an answer", [], None

    async def test_a_spinner_covers_the_wait_for_the_response(self):
        await self.client.process_query("hello")

        self.assertTrue(self.status_active_during_request)
        self.assertIn("waiting for", self.statuses[0].message)

    async def test_the_spinner_is_gone_before_the_stream_renders(self):
        # Two live displays at once garble each other, and the streaming
        # manager starts its own as soon as it is handed the stream.
        await self.client.process_query("hello")

        self.assertFalse(self.status_active_during_streaming)
        self.assertTrue(self.statuses[0].was_entered)


if __name__ == "__main__":
    unittest.main()
