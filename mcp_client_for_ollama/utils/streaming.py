"""
This file implements streaming functionality for the MCP client for Ollama.

Classes:
    StreamingManager: Handles streaming responses from Ollama.
"""
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from .metrics import display_metrics, extract_metrics

class StreamingManager:
    """Manages streaming responses for Ollama API calls"""

    def __init__(self, console):
        """Initialize the streaming manager

        Args:
            console: Rich console for output
        """
        self.console = console

    def _create_working_display(self):
        """Create a display showing working status with spinner"""
        table = Table.grid()
        spinner = Spinner("dots", style="cyan")
        working_text = Text("working...", style="cyan")
        header = Table.grid(padding=(0, 1))
        header.add_row(spinner, working_text)
        table.add_row(header)
        return table

    def _create_content_display(self, content, thinking_content="", show_thinking=True, has_tool_calls=False):
        """Create a display for content with optional thinking section"""
        if thinking_content and show_thinking:
            # Only add separator and Answer label if there's actual content
            if content:
                if has_tool_calls:
                    combined_content = thinking_content + "\n\n---\n\n" + content
                else:
                    combined_content = thinking_content + "\n\n---\n\n**Answer:**\n\n" + content
            else:
                # No content, just show thinking
                combined_content = thinking_content
            return Markdown(combined_content)
        else:
            # Don't add "Answer:" label when tools are being called or when content is empty
            if has_tool_calls or not content:
                return Markdown(content)
            else:
                return Markdown("**Answer:**\n\n" + content)

    async def process_streaming_response(self, stream, print_response=True, thinking_mode=False, show_thinking=True, show_metrics=False):
        """Process a streaming response from Ollama with status spinner and content updates

        Args:
            stream: Async iterator of response chunks
            print_response: Flag to control live updating of response text
            thinking_mode: Whether to handle thinking mode responses
            show_thinking: Whether to keep thinking text visible in final output
            show_metrics: Whether to display performance metrics when streaming completes

        Returns:
            str: Accumulated response text
            list: Tool calls if any
            dict: Metrics if captured, None otherwise
        """
        accumulated_text = ""
        thinking_content = ""
        tool_calls = []
        showing_working = True  # Track if we're still showing the working display
        metrics = None  # Store metrics from final chunk

        if print_response:
            with Live(console=self.console, refresh_per_second=10, vertical_overflow='visible') as live:
                # Start with working display
                live.update(self._create_working_display())

                async for chunk in stream:
                    # Capture metrics when chunk is done
                    extracted_metrics = extract_metrics(chunk)
                    if extracted_metrics:
                        metrics = extracted_metrics

                    # Handle thinking content
                    if (thinking_mode and hasattr(chunk, 'message') and
                        hasattr(chunk.message, 'thinking') and chunk.message.thinking):

                        if not thinking_content:
                            thinking_content = "🤔 **Thinking:**\n\n"
                        thinking_content += chunk.message.thinking

                        # Hide working display and show thinking content
                        if showing_working:
                            showing_working = False

                        display = self._create_content_display(
                            accumulated_text, thinking_content, show_thinking=True, has_tool_calls=False
                        )
                        live.update(display)

                    # Handle regular content
                    if (hasattr(chunk, 'message') and hasattr(chunk.message, 'content') and
                        chunk.message.content):

                        accumulated_text += chunk.message.content

                        # Hide working display and show content
                        if showing_working:
                            showing_working = False

                        # Update display based on thinking mode
                        display = self._create_content_display(
                            accumulated_text, thinking_content, show_thinking, has_tool_calls=False
                        )
                        live.update(display)

                    # Handle tool calls
                    if (hasattr(chunk, 'message') and hasattr(chunk.message, 'tool_calls') and
                        chunk.message.tool_calls):
                        # Hide working display and show final content if any before tool calls
                        showing_working = False

                        for tool in chunk.message.tool_calls:
                            tool_calls.append(tool)

                        # Show final content display if we have any accumulated text
                        if accumulated_text or thinking_content:
                            display = self._create_content_display(
                                accumulated_text, thinking_content, show_thinking, has_tool_calls=True
                            )
                            live.update(display)
                        else:
                            # Clear the working display by showing empty content
                            live.update(Markdown(""))

            # Add spacing after streaming completes only if we showed content and no tool calls
            if not showing_working and not tool_calls:
                self.console.print()

            # Display metrics if requested and available
            if show_metrics and metrics and print_response:
                display_metrics(self.console, metrics)
        else:
            # Silent processing without display
            async for chunk in stream:
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

        return accumulated_text, tool_calls, metrics
