"""
This file implements streaming functionality for the MCP client for Ollama.

Classes:
    StreamingManager: Handles streaming responses from Ollama.
"""
from rich.markdown import Markdown
from .metrics import display_metrics, extract_metrics

class StreamingManager:
    """Manages streaming responses for Ollama API calls"""

    def __init__(self, console):
        """Initialize the streaming manager

        Args:
            console: Rich console for output
        """
        self.console = console

    async def process_streaming_response(self, stream, print_response=True, thinking_mode=False, show_thinking=True, show_metrics=False, cancellation_check=None):
        """Process a streaming response from Ollama with status spinner and content updates

        Args:
            stream: Async iterator of response chunks
            print_response: Flag to control live updating of response text
            thinking_mode: Whether to handle thinking mode responses
            show_thinking: Whether to keep thinking text visible in final output
            show_metrics: Whether to display performance metrics when streaming completes
            cancellation_check: Optional callable that returns True if processing should be cancelled

        Returns:
            str: Accumulated response text
            list: Tool calls if any
            dict: Metrics if captured, None otherwise
            list: Logprobs data if available, None otherwise
        """
        accumulated_text = ""
        thinking_content = ""
        tool_calls = []
        metrics = None  # Store metrics from final chunk
        logprobs_data = []  # Store logprobs from chunks

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
                        return accumulated_text, tool_calls, metrics, logprobs_data

                    # Capture metrics when chunk is done
                    extracted_metrics = extract_metrics(chunk)
                    if extracted_metrics:
                        metrics = extracted_metrics

                    # Capture logprobs if present (at response level, not message level)
                    if hasattr(chunk, 'logprobs') and chunk.logprobs:
                        logprobs_data.extend(chunk.logprobs)

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
                        if not accumulated_text:
                            self.console.print()
                            self.console.print(Markdown("📝 **Answer:**"))
                            self.console.print(Markdown("---"))
                            self.console.print()

                        accumulated_text += chunk.message.content

                        # Print only new content as plain text (will render full markdown at end)
                        self.console.print(chunk.message.content, end="")

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
                status.stop()

            # Print newline at end
            self.console.print()
            # Render final markdown content properly
            if accumulated_text:
                # Render in markdown format and state this
                self.console.print()
                self.console.print(Markdown("📝 **Answer (Markdown):**"))
                self.console.print(Markdown("---"))
                self.console.print()
                self.console.print(Markdown(accumulated_text))
                self.console.print()

        else:
            # Silent processing without display
            async for chunk in stream:
                # Check for cancellation
                if cancellation_check and cancellation_check():
                    return accumulated_text, tool_calls, metrics, logprobs_data

                # Capture metrics when chunk is done
                extracted_metrics = extract_metrics(chunk)
                if extracted_metrics:
                    metrics = extracted_metrics

                # Capture logprobs if present (at response level, not message level)
                if hasattr(chunk, 'logprobs') and chunk.logprobs:
                    logprobs_data.extend(chunk.logprobs)

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

        return accumulated_text, tool_calls, metrics, logprobs_data
