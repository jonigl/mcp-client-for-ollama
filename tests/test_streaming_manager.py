"""Tests for streaming answer rendering modes."""

import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from mcp_client_for_ollama.utils.streaming import StreamingManager


@dataclass
class DummyMessage:
    """Minimal message double for streaming tests."""

    content: str = ""
    thinking: str = ""
    tool_calls: list = None


@dataclass
class DummyChunk:
    """Minimal chunk double for streaming tests."""

    message: DummyMessage


async def _stream_chunks(*chunks):
    """Yield chunks for the streaming manager."""
    for chunk in chunks:
        yield chunk


class FakeLive:
    """Live renderer double that records updates."""

    instances = []

    def __init__(self, renderable, console, refresh_per_second, transient, auto_refresh=True, vertical_overflow="ellipsis"):
        self.renderable = renderable
        self.console = console
        self.refresh_per_second = refresh_per_second
        self.transient = transient
        self.auto_refresh = auto_refresh
        self.vertical_overflow = vertical_overflow
        self.started = False
        self.stopped = False
        self.updates = []
        type(self).instances.append(self)

    def start(self):
        self.started = True

    def update(self, renderable, refresh=False):
        self.renderable = renderable
        self.updates.append((renderable, refresh))

    def stop(self):
        self.stopped = True


class TestStreamingManager(unittest.IsolatedAsyncioTestCase):
    """Validate answer rendering modes without hitting the terminal."""

    def setUp(self):
        self.console = MagicMock()
        self.status = MagicMock()
        self.console.status.return_value = self.status
        FakeLive.instances.clear()

    async def test_plain_mode_skips_final_markdown_render(self):
        manager = StreamingManager(self.console)

        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"), patch(
            "mcp_client_for_ollama.utils.streaming.extract_metrics",
            return_value=None,
        ):
            response_text, tool_calls, metrics = await manager.process_streaming_response(
                _stream_chunks(DummyChunk(DummyMessage(content="hello **world**"))),
                answer_render_mode="plain",
            )

        printed = [call.args[0] for call in self.console.print.call_args_list if call.args]

        self.assertEqual(response_text, "hello **world**")
        self.assertEqual(tool_calls, [])
        self.assertIsNone(metrics)
        self.assertIn("MD::📝 **Answer:**", printed)
        self.assertIn("hello **world**", printed)
        self.assertNotIn("MD::📝 **Answer (Markdown):**", printed)

    async def test_both_mode_keeps_plain_stream_and_final_markdown(self):
        manager = StreamingManager(self.console)

        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"), patch(
            "mcp_client_for_ollama.utils.streaming.extract_metrics",
            return_value=None,
        ):
            response_text, _, _ = await manager.process_streaming_response(
                _stream_chunks(DummyChunk(DummyMessage(content="hello **world**"))),
                answer_render_mode="both",
            )

        printed = [call.args[0] for call in self.console.print.call_args_list if call.args]

        self.assertEqual(response_text, "hello **world**")
        self.assertIn("MD::📝 **Answer:**", printed)
        self.assertIn("MD::📝 **Answer (Markdown):**", printed)
        self.assertIn("hello **world**", printed)

    async def test_markdown_mode_uses_live_rendering_only(self):
        manager = StreamingManager(self.console)

        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"), patch(
            "mcp_client_for_ollama.utils.streaming.Live",
            FakeLive,
        ), patch(
            "mcp_client_for_ollama.utils.streaming.extract_metrics",
            return_value=None,
        ), patch(
            "mcp_client_for_ollama.utils.streaming.monotonic",
            side_effect=[0.0, 1.0],
        ):
            response_text, _, _ = await manager.process_streaming_response(
                _stream_chunks(
                    DummyChunk(DummyMessage(content="hello ")),
                    DummyChunk(DummyMessage(content="**world**")),
                ),
                answer_render_mode="markdown",
            )

        printed = [call.args[0] for call in self.console.print.call_args_list if call.args]
        self.assertEqual(response_text, "hello **world**")
        self.assertNotIn("MD::📝 **Answer:**", printed)
        self.assertNotIn("hello ", printed)
        self.assertEqual(printed.count("MD::📝 **Answer (Markdown):**"), 1)
        self.assertEqual(len(FakeLive.instances), 1)

        live = FakeLive.instances[0]
        self.assertTrue(live.started)
        self.assertTrue(live.stopped)
        self.assertEqual(live.renderable, "MD::hello **world**")
        self.assertTrue(any(refresh for _, refresh in live.updates))


if __name__ == "__main__":
    unittest.main()
