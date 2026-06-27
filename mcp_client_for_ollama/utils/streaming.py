"""
This file implements streaming functionality for the MCP client for Ollama.

Classes:
    ProgressiveMarkdownRenderer: Progressive markdown renderer.
    StreamingManager: Handles streaming responses from Ollama.
"""
import shutil
from time import monotonic

from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from .metrics import display_metrics, extract_metrics


class ProgressiveMarkdownRenderer:
    """Progressive markdown renderer.

    Uses Rich Live with vertical_overflow="crop" to prevent scrollback
    corruption, and progressively commits stable content above the Live
    zone via console.print()
    """

    REFRESH_INTERVAL = 0.15
    VIEWPORT_COMMIT_THRESHOLD = 0.6

    def __init__(self, console):
        self.console = console
        self.full_text = ""
        self.committed_text = ""
        self._live = None
        self._last_refresh = 0.0

    def start(self):
        """Start the live rendering zone."""
        self._live = Live(
            Text(""),
            console=self.console,
            vertical_overflow="crop",
            refresh_per_second=15,
            transient=True,
        )
        self._live.start()
        self._last_refresh = monotonic()

    def update(self, new_chunk):
        """Append a new chunk and refresh the display (throttled)."""
        self.full_text += new_chunk

        now = monotonic()
        if now - self._last_refresh < self.REFRESH_INTERVAL:
            return
        self._last_refresh = now

        self._maybe_commit()
        uncommitted = self.full_text[len(self.committed_text):]
        if uncommitted:
            self._live.update(Markdown(uncommitted), refresh=True)

    def finish(self):
        """Commit all remaining content and cleanly stop the Live zone."""
        if self._live is None:
            return

        # Commit whatever remains
        remaining = self.full_text[len(self.committed_text):]
        if remaining:
            self._print_markdown_preserving_trailing_newlines(remaining)
            self.committed_text = self.full_text

        # Clear the live zone (transient=True will erase it) and stop
        self._live.update(Text(""), refresh=True)
        self._live.stop()
        self._live = None

    def _maybe_commit(self):
        """Commit content above the Live zone if uncommitted text is tall."""
        uncommitted = self.full_text[len(self.committed_text):]
        if not uncommitted:
            return

        terminal_size = shutil.get_terminal_size()
        term_lines = terminal_size.lines
        viewport_height = max(1, term_lines - 2)  # Ensure positive value for edge cases
        threshold = int(viewport_height * self.VIEWPORT_COMMIT_THRESHOLD)

        estimated_height = self._estimate_height(uncommitted, terminal_size.columns)
        if estimated_height <= threshold:
            return

        commit_point = self._find_safe_commit_point(uncommitted)
        if commit_point is None:
            # No paragraph boundary, but the live zone is taller than the
            # threshold. Fall back to the last single-newline boundary so the
            # zone stays bounded and rich.Live can still erase prior frames.
            commit_point = self._find_fallback_commit_point(uncommitted)
        if commit_point is None:
            return

        text_to_commit = uncommitted[:commit_point]
        self._print_markdown_preserving_trailing_newlines(text_to_commit)
        self.committed_text += text_to_commit

    def _print_markdown_preserving_trailing_newlines(self, text):
        """Render markdown while preserving source trailing blank lines.

        Rich markdown rendering may collapse trailing blank lines when content is
        split into progressive commits. Preserve newline count explicitly so
        spacing between committed and live content remains stable.
        """
        if not text:
            return

        trailing_newlines = len(text) - len(text.rstrip("\n"))
        markdown_text = text[:-trailing_newlines] if trailing_newlines else text

        if markdown_text:
            self.console.print(Markdown(markdown_text))
            if trailing_newlines > 1:
                self.console.print(end="\n" * (trailing_newlines - 1))
            return

        self.console.print(end="\n" * trailing_newlines)

    def _estimate_height(self, text, terminal_width):
        """Rough estimate of how many terminal lines text will occupy."""
        lines = 0
        for line in text.split("\n"):
            # Each line wraps based on terminal width (rough: ignore markup)
            if terminal_width > 0:
                wrapped_lines = max(1, (len(line) + terminal_width - 1) // terminal_width)
            else:
                wrapped_lines = 1
            lines += wrapped_lines
        return lines

    def _find_safe_commit_point(self, text):
        """Find the last paragraph boundary (\\n\\n) not inside a fenced code block.

        Returns the index (end of the committed portion) or None if no safe point.
        """
        # We need at least some minimum content to commit
        if len(text) < 20:
            return None

        # Track fenced code block state and find safe paragraph breaks
        in_code_block = False
        last_safe_break = None
        pos = 0

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            # Check for paragraph boundary: empty line outside code block
            if not in_code_block and stripped == "":
                # Include the newline in the break point
                break_pos = pos + len(line) + 1
                if break_pos < len(text):  # Don't commit everything
                    last_safe_break = break_pos

            pos += len(line) + 1  # Move past this line and its newline

        return last_safe_break

    def _find_fallback_commit_point(self, text):
        """Find the last single-newline boundary not inside a fenced code block.

        Used when content is taller than the viewport but has no paragraph
        boundary to commit at. Commits up to the last newline, leaving only the
        final (in-progress) line in the Live zone. Returns the index or None if
        no safe point exists (e.g. inside a code fence or a single long line).
        """
        in_code_block = False
        last_safe_break = None
        pos = 0

        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            pos += len(line) + 1  # Move past this line and its newline

            # Safe to break after this line if we're outside a code block and
            # there is a following line to keep in the Live zone.
            if not in_code_block and i < len(lines) - 1 and pos < len(text):
                last_safe_break = pos

        return last_safe_break


class BlockMarkdownRenderer(ProgressiveMarkdownRenderer):
    """Append-only markdown renderer.

    Prints each completed markdown block (paragraph/list/table/code fence) once
    via console.print and never redraws it. Because nothing is ever erased, it
    cannot exhibit the rich.Live cursor-miscount duplication that occurs with
    wide glyphs (emoji) or terminal resizes.
    """

    def start(self):
        """No live zone; just reset the refresh throttle."""
        self._last_refresh = monotonic()

    def update(self, new_chunk):
        """Append a chunk and flush any completed blocks (throttled)."""
        self.full_text += new_chunk
        now = monotonic()
        if now - self._last_refresh < self.REFRESH_INTERVAL:
            return
        self._last_refresh = now
        self._commit_complete_blocks()

    def finish(self):
        """Flush whatever remains as a final markdown block."""
        remaining = self.full_text[len(self.committed_text):]
        if remaining:
            self._print_markdown_preserving_trailing_newlines(remaining)
            self.committed_text = self.full_text

    def _commit_complete_blocks(self):
        """Commit complete paragraphs; flush lines if a block grows too tall."""
        uncommitted = self.full_text[len(self.committed_text):]
        if not uncommitted:
            return
        commit_point = self._find_safe_commit_point(uncommitted)
        if commit_point is None:
            # No completed paragraph yet. If the in-progress block is already
            # taller than the viewport, flush its completed lines so long prose
            # keeps flowing; otherwise wait for more content.
            terminal_size = shutil.get_terminal_size()
            viewport_height = max(1, terminal_size.lines - 2)
            threshold = int(viewport_height * self.VIEWPORT_COMMIT_THRESHOLD)
            if self._estimate_height(uncommitted, terminal_size.columns) > threshold:
                commit_point = self._find_fallback_commit_point(uncommitted)
        if commit_point is None:
            return
        self._print_markdown_preserving_trailing_newlines(uncommitted[:commit_point])
        self.committed_text += uncommitted[:commit_point]


class StreamingManager:
    """Manages streaming responses for Ollama API calls"""

    VALID_ANSWER_RENDER_MODES = {"plain", "markdown", "both", "blocks"}

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

    def _print_answer_transition_header(self, show_thinking, render_mode):
        """Separate visible thinking output from the answer header."""
        self.console.print()
        if show_thinking:
            self.console.print()

        if render_mode == "markdown":
            self.console.print(Markdown("📝 **Answer (Markdown):**"))
        else:
            self.console.print(Markdown("📝 **Answer:**"))
        self.console.print(Markdown("---"))
        self.console.print()

    def _render_final_markdown_answer(self, accumulated_text):
        """Render the completed markdown answer below the streamed output."""
        self._print_answer_transition_header(False, "markdown")
        self.console.print(Markdown(accumulated_text))
        self.console.print()

    async def process_streaming_response(self, stream, print_response=True, thinking_mode=False, show_thinking=True, show_metrics=False, answer_render_mode="both", cancellation_check=None):
        """Process a streaming response from Ollama with status spinner and content updates

        Args:
            stream: Async iterator of ChatCompletionChunk objects
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
        progressive_renderer = None

        if print_response:
            # Thinking header flag
            thinking_started = False
            # Show initial working spinner until first chunk arrives
            first_chunk = True
            self.console.print("\n[bold bright_magenta](New!)[/bold bright_magenta] [yellow]You can press 'a' to abort generation.[/yellow]\n")
            status = self.console.status("[cyan]working...", spinner="dots")
            status.start()

            # Buffer for incremental tool call deltas
            tool_call_buffers = {}

            try:
                stream_iter = stream.__aiter__()
                while True:
                    try:
                        chunk = await stream_iter.__anext__()
                    except StopAsyncIteration:
                        break
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).debug("Skipping unparseable stream chunk: %s", e)
                        continue

                    # Check for cancellation
                    if cancellation_check and cancellation_check():
                        self.console.print("\n[yellow]Generation aborted by user.[/yellow]")
                        return accumulated_text, tool_calls, metrics

                    # Capture metrics when chunk carries usage data
                    extracted_metrics = extract_metrics(chunk)
                    if extracted_metrics:
                        metrics = extracted_metrics

                    if not getattr(chunk, "choices", None):
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    # Handle thinking content
                    thinking = None
                    reasoning = getattr(delta, "reasoning", None)
                    if reasoning is not None:
                        thinking = reasoning.content if hasattr(reasoning, "content") else (reasoning if isinstance(reasoning, str) else None)

                    if thinking_mode and thinking:
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
                        thinking_content += thinking
                        if show_thinking:
                            self.console.print(thinking, end="")

                    # Handle regular content
                    content = getattr(delta, "content", None) or ""
                    if content:
                        if first_chunk:
                            status.stop()
                            first_chunk = False
                        if not accumulated_text and stream_plain_text:
                            self._print_answer_transition_header(show_thinking, "plain")
                        accumulated_text += content
                        if stream_plain_text:
                            self.console.print(content, end="")
                        elif render_mode in {"markdown", "blocks"}:
                            if progressive_renderer is None:
                                self._print_answer_transition_header(show_thinking, "markdown")
                                renderer_cls = (
                                    BlockMarkdownRenderer if render_mode == "blocks"
                                    else ProgressiveMarkdownRenderer
                                )
                                progressive_renderer = renderer_cls(self.console)
                                progressive_renderer.start()
                            progressive_renderer.update(content)

                    # Buffer incremental tool call deltas
                    delta_tool_calls = getattr(delta, "tool_calls", None)
                    if delta_tool_calls:
                        if first_chunk:
                            status.stop()
                            first_chunk = False
                        for tc in delta_tool_calls:
                            idx = tc.index if hasattr(tc, "index") else 0
                            if idx not in tool_call_buffers:
                                tool_call_buffers[idx] = {"id": "", "name": "", "arguments": ""}
                            buf = tool_call_buffers[idx]
                            if getattr(tc, "id", None):
                                buf["id"] = tc.id
                            if hasattr(tc, "function") and tc.function:
                                if getattr(tc.function, "name", None):
                                    buf["name"] += tc.function.name
                                if getattr(tc.function, "arguments", None):
                                    buf["arguments"] += tc.function.arguments

                    # On finish, emit completed tool calls
                    if getattr(choice, "finish_reason", None) and tool_call_buffers:
                        for idx, buf in sorted(tool_call_buffers.items()):
                            tool_calls.append({
                                "id": buf["id"] or f"call_{idx}",
                                "type": "function",
                                "function": {"name": buf["name"], "arguments": buf["arguments"]},
                            })
                        tool_call_buffers.clear()

            finally:
                if progressive_renderer is not None:
                    progressive_renderer.finish()
                status.stop()

            # Print newline at end
            if accumulated_text and stream_plain_text:
                self.console.print()
            # Render final markdown content properly (for "both" mode where progressive_renderer wasn't used)
            if accumulated_text and render_markdown and progressive_renderer is None:
                self._render_final_markdown_answer(accumulated_text)

        else:
            # Silent processing without display
            tool_call_buffers = {}
            stream_iter = stream.__aiter__()
            while True:
                try:
                    chunk = await stream_iter.__anext__()
                except StopAsyncIteration:
                    break
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).debug("Skipping unparseable stream chunk: %s", e)
                    continue

                # Check for cancellation
                if cancellation_check and cancellation_check():
                    return accumulated_text, tool_calls, metrics

                extracted_metrics = extract_metrics(chunk)
                if extracted_metrics:
                    metrics = extracted_metrics

                if not getattr(chunk, "choices", None):
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                reasoning = getattr(delta, "reasoning", None)
                if thinking_mode and reasoning is not None:
                    thinking = reasoning.content if hasattr(reasoning, "content") else (reasoning if isinstance(reasoning, str) else None)
                    if thinking:
                        thinking_content += thinking

                content = getattr(delta, "content", None) or ""
                if content:
                    accumulated_text += content

                delta_tool_calls = getattr(delta, "tool_calls", None)
                if delta_tool_calls:
                    for tc in delta_tool_calls:
                        idx = tc.index if hasattr(tc, "index") else 0
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {"id": "", "name": "", "arguments": ""}
                        buf = tool_call_buffers[idx]
                        if getattr(tc, "id", None):
                            buf["id"] = tc.id
                        if hasattr(tc, "function") and tc.function:
                            if getattr(tc.function, "name", None):
                                buf["name"] += tc.function.name
                            if getattr(tc.function, "arguments", None):
                                buf["arguments"] += tc.function.arguments

                if getattr(choice, "finish_reason", None) and tool_call_buffers:
                    for idx, buf in sorted(tool_call_buffers.items()):
                        tool_calls.append({
                            "id": buf["id"] or f"call_{idx}",
                            "type": "function",
                            "function": {"name": buf["name"], "arguments": buf["arguments"]},
                        })
                    tool_call_buffers.clear()

        # Display metrics if requested
        if show_metrics and metrics:
            display_metrics(self.console, metrics)

        return accumulated_text, tool_calls, metrics
