"""Tests for streaming answer rendering modes."""

import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from mcp_client_for_ollama.utils.streaming import ProgressiveMarkdownRenderer, StreamingManager


@dataclass
class DummyDelta:
    """Minimal delta double for streaming tests."""

    content: str = ""
    reasoning: str = None
    tool_calls: list = None


@dataclass
class DummyChoice:
    """Minimal choice double for streaming tests."""

    delta: DummyDelta
    finish_reason: str = None


@dataclass
class DummyChunk:
    """Minimal chunk double for streaming tests."""

    choices: list
    usage: object = None


async def _stream_chunks(*chunks):
    """Yield chunks for the streaming manager."""
    for chunk in chunks:
        yield chunk


class FakeLive:
    """Live renderer double that records updates."""

    instances = []

    def __init__(self, renderable, console, refresh_per_second=4, transient=False, vertical_overflow="ellipsis"):
        self.renderable = renderable
        self.console = console
        self.refresh_per_second = refresh_per_second
        self.transient = transient
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


class TestableProgressiveMarkdownRenderer(ProgressiveMarkdownRenderer):
    """Test helper exposing stable wrappers around internal renderer methods."""

    def print_markdown_preserving_trailing_newlines(self, text):
        self._print_markdown_preserving_trailing_newlines(text)

    def estimate_height(self, text, terminal_width):
        return self._estimate_height(text, terminal_width)


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
                _stream_chunks(DummyChunk(choices=[DummyChoice(DummyDelta(content="hello **world**"))])),
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
                _stream_chunks(DummyChunk(choices=[DummyChoice(DummyDelta(content="hello **world**"))])),
                answer_render_mode="both",
            )

        printed = [call.args[0] for call in self.console.print.call_args_list if call.args]

        self.assertEqual(response_text, "hello **world**")
        self.assertIn("MD::📝 **Answer:**", printed)
        self.assertIn("MD::📝 **Answer (Markdown):**", printed)
        self.assertIn("hello **world**", printed)

    async def test_markdown_mode_uses_progressive_renderer(self):
        manager = StreamingManager(self.console)

        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"), patch(
            "mcp_client_for_ollama.utils.streaming.Live",
            FakeLive,
        ), patch(
            "mcp_client_for_ollama.utils.streaming.Text",
            side_effect=lambda text: f"TEXT::{text}",
        ), patch(
            "mcp_client_for_ollama.utils.streaming.extract_metrics",
            return_value=None,
        ), patch(
            "mcp_client_for_ollama.utils.streaming.monotonic",
            side_effect=[0.0, 0.0, 1.0, 2.0],
        ):
            response_text, _, _ = await manager.process_streaming_response(
                _stream_chunks(
                    DummyChunk(choices=[DummyChoice(DummyDelta(content="hello "))]),
                    DummyChunk(choices=[DummyChoice(DummyDelta(content="**world**"))]),
                ),
                answer_render_mode="markdown",
            )

        printed = [call.args[0] for call in self.console.print.call_args_list if call.args]
        self.assertEqual(response_text, "hello **world**")
        # Should NOT have plain-mode answer header
        self.assertNotIn("MD::📝 **Answer:**", printed)
        # Should have markdown answer header
        self.assertEqual(printed.count("MD::📝 **Answer (Markdown):**"), 1)
        # Progressive renderer creates one Live instance
        self.assertEqual(len(FakeLive.instances), 1)

        live = FakeLive.instances[0]
        self.assertTrue(live.started)
        self.assertTrue(live.stopped)
        # Progressive renderer uses transient=True and vertical_overflow="crop"
        self.assertTrue(live.transient)
        self.assertEqual(live.vertical_overflow, "crop")
        # Final content is committed via console.print (the finish() call)
        # The last update should clear the live zone
        self.assertTrue(any(refresh for _, refresh in live.updates))

    async def test_visible_thinking_gets_blank_line_before_answer_header(self):
        manager = StreamingManager(self.console)

        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"), patch(
            "mcp_client_for_ollama.utils.streaming.extract_metrics",
            return_value=None,
        ):
            response_text, _, _ = await manager.process_streaming_response(
                _stream_chunks(
                    DummyChunk(choices=[DummyChoice(DummyDelta(reasoning="planning"))]),
                    DummyChunk(choices=[DummyChoice(DummyDelta(content="answer"))]),
                ),
                thinking_mode=True,
                show_thinking=True,
                answer_render_mode="plain",
            )

        calls = self.console.print.call_args_list
        thinking_index = next(
            index for index, call in enumerate(calls) if call.args and call.args[0] == "planning"
        )

        self.assertEqual(response_text, "answer")
        self.assertEqual(calls[thinking_index].kwargs.get("end"), "")
        self.assertEqual(calls[thinking_index + 1].args, ())
        self.assertEqual(calls[thinking_index + 2].args, ())
        self.assertEqual(calls[thinking_index + 3].args, ("MD::📝 **Answer:**",))


class TestProgressiveMarkdownRenderer(unittest.TestCase):
    """Validate renderer helpers used by markdown-only streaming mode."""

    def setUp(self):
        self.console = MagicMock()
        self.renderer = TestableProgressiveMarkdownRenderer(self.console)

    def test_preserves_trailing_newline_spacing(self):
        with patch("mcp_client_for_ollama.utils.streaming.Markdown", side_effect=lambda text: f"MD::{text}"):
            self.renderer.print_markdown_preserving_trailing_newlines("alpha\n\n")

        self.console.print.assert_any_call("MD::alpha")
        self.console.print.assert_any_call(end="\n")

    def test_estimate_height_exact_width_is_single_line(self):
        estimated_height = self.renderer.estimate_height("abcd", terminal_width=4)
        self.assertEqual(estimated_height, 1)

    def test_estimate_height_wraps_when_exceeding_width(self):
        estimated_height = self.renderer.estimate_height("abcde", terminal_width=4)
        self.assertEqual(estimated_height, 2)


if __name__ == "__main__":
    unittest.main()
