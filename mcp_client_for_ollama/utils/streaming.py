"""
This file implements streaming functionality for the MCP client for Ollama.

Classes:
    StreamingManager: Handles streaming responses from Ollama.
"""
from time import monotonic

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown

from .metrics import display_metrics, extract_metrics

class StreamingManager:
    """Manages streaming responses for Ollama API calls"""

    LIVE_MARKDOWN_REFRESH_INTERVAL = 0.15
    VALID_ANSWER_RENDER_MODES = {"plain", "markdown", "both"}

    def __init__(self, console):
        """Initialize the streaming manager

        Args:
            console: Rich console for output
        """
        self.console = console

    def _normalize_answer_render_mode(self, answer_render_mode):
        """Return a supported answer rendering mode."""
        if answer_render_mode in self.VALID_ANSWER_RENDER_MODES:
            return answer_render_mode
        return "both"

    def _build_markdown_answer_renderable(self, accumulated_text):
        """Build the markdown-only answer renderable."""
        return Group(
            Markdown("📝 **Answer (Markdown):**"),
            Markdown("---"),
            Markdown(accumulated_text)
        )

    def _render_final_markdown_answer(self, accumulated_text):
        """Render the completed markdown answer below the streamed output."""
        self.console.print()
        self.console.print(Markdown("📝 **Answer (Markdown):**"))
        self.console.print(Markdown("---"))
        self.console.print()
        self.console.print(Markdown(accumulated_text))
        self.console.print()

    async def process_streaming_response(self, stream, print_response=True, thinking_mode=False, show_thinking=True, show_metrics=False, answer_render_mode="both", cancellation_check=None):
        """Process a streaming response from Ollama with status spinner and content updates

        Args:
            stream: Async iterator of response chunks
            print_response: Flag to control live updating of response text
            thinking_mode: Whether to handle thinking mode responses
            show_thinking: Whether to keep thinking text visible in final output
            show_metrics: Whether to display performance metrics when streaming completes
            answer_render_mode: One of plain, markdown, or both for answer rendering
            cancellation_check: Optional callable that returns True if processing should be cancelled

        Returns:
            str: Accumulated response text
            list: Tool calls if any
            dict: Metrics if captured, None otherwise
        """
        accumulated_text = ""
        thinking_content = ""
        tool_calls = []
        metrics = None  # Store metrics from final chunk
        render_mode = self._normalize_answer_render_mode(answer_render_mode)
        stream_plain_text = render_mode in {"plain", "both"}
        render_markdown = render_mode in {"markdown", "both"}
        live_markdown = None
        last_live_markdown_refresh = 0.0

        if print_response:
            # Thinking header flag
            thinking_started = False
            # Show initial working spinner until first chunk arrives
            first_chunk = True
            self.console.print("\n[bold bright_magenta](New!)[/bold bright_magenta] [yellow]You can press 'a' to abort generation.[/yellow]\n")
            status = self.console.status("[cyan]working...", spinner="dots")
            status.start()


            try:
                async for chunk in stream:
                    # Check for cancellation
                    if cancellation_check and cancellation_check():
                        self.console.print("\n[yellow]Generation aborted by user.[/yellow]")
                        return accumulated_text, tool_calls, metrics

                    # Capture metrics when chunk is done
                    extracted_metrics = extract_metrics(chunk)
                    if extracted_metrics:
                        metrics = extracted_metrics

                    # Handle thinking content
                    if (thinking_mode and hasattr(chunk, 'message') and
                        hasattr(chunk.message, 'thinking') and chunk.message.thinking):
                        # Stop spinner on first thinking chunk ONLY if show_thinking is True
                        if first_chunk and show_thinking:
                            status.stop()
                            first_chunk = False

                        if not thinking_content:
                            thinking_content = "🤔 **Thinking:**\n\n"
                            if not thinking_started and show_thinking:
                                self.console.print(Markdown("🤔 **Thinking:**\n"))
                                self.console.print(Markdown("---"))
                                self.console.print()
                                thinking_started = True
                        thinking_content += chunk.message.thinking
                        # Print thinking content as plain text only if show_thinking is True
                        if show_thinking:
                            self.console.print(chunk.message.thinking, end="")

                    # Handle regular content
                    if (hasattr(chunk, 'message') and hasattr(chunk.message, 'content') and
                        chunk.message.content):
                        # Stop spinner on first content chunk (always)
                        if first_chunk:
                            status.stop()
                            first_chunk = False

                        # Print separator and Answer label when transitioning from thinking to content
                        if not accumulated_text and stream_plain_text:
                            self.console.print()
                            self.console.print(Markdown("📝 **Answer:**"))
                            self.console.print(Markdown("---"))
                            self.console.print()

                        accumulated_text += chunk.message.content

                        # Print only new content as plain text (will render full markdown at end)
                        if stream_plain_text:
                            self.console.print(chunk.message.content, end="")
                        elif render_mode == "markdown":
                            if live_markdown is None:
                                self.console.print()
                                live_markdown = Live(
                                    self._build_markdown_answer_renderable(accumulated_text),
                                    console=self.console,
                                    refresh_per_second=8,
                                    transient=False,
                                )
                                live_markdown.start()
                                last_live_markdown_refresh = monotonic()
                            else:
                                current_time = monotonic()
                                if current_time - last_live_markdown_refresh >= self.LIVE_MARKDOWN_REFRESH_INTERVAL:
                                    live_markdown.update(
                                        self._build_markdown_answer_renderable(accumulated_text),
                                        refresh=True,
                                    )
                                    last_live_markdown_refresh = current_time

                    # Handle tool calls
                    if (hasattr(chunk, 'message') and hasattr(chunk.message, 'tool_calls') and
                        chunk.message.tool_calls):
                        # Stop spinner on first tool call chunk (always) - just in case no content arrives
                        if first_chunk:
                            status.stop()
                            first_chunk = False

                        for tool in chunk.message.tool_calls:
                            tool_calls.append(tool)
            finally:
                if live_markdown is not None:
                    live_markdown.update(
                        self._build_markdown_answer_renderable(accumulated_text),
                        refresh=True,
                    )
                    live_markdown.stop()
                status.stop()

            # Print newline at end
            if accumulated_text and stream_plain_text:
                self.console.print()
            # Render final markdown content properly
            if accumulated_text and render_markdown and live_markdown is None:
                self._render_final_markdown_answer(accumulated_text)

        else:
            # Silent processing without display
            async for chunk in stream:
                # Check for cancellation
                if cancellation_check and cancellation_check():
                    return accumulated_text, tool_calls, metrics

                # Capture metrics when chunk is done
                extracted_metrics = extract_metrics(chunk)
                if extracted_metrics:
                    metrics = extracted_metrics

                if (thinking_mode and hasattr(chunk, 'message') and
                    hasattr(chunk.message, 'thinking') and chunk.message.thinking):
                    thinking_content += chunk.message.thinking

                if (hasattr(chunk, 'message') and hasattr(chunk.message, 'content') and
                    chunk.message.content):
                    accumulated_text += chunk.message.content

                if (hasattr(chunk, 'message') and hasattr(chunk.message, 'tool_calls') and
                    chunk.message.tool_calls):
                    for tool in chunk.message.tool_calls:
                        tool_calls.append(tool)

        # Display metrics if requested
        if show_metrics and metrics:
            display_metrics(self.console, metrics)

        return accumulated_text, tool_calls, metrics
