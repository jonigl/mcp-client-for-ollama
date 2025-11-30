"""
This file implements streaming functionality for the MCP client for Ollama.

Classes:
    StreamingManager: Handles streaming responses from Ollama.
"""
import json
from ollama._types import Message
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
        metrics = None  # Store metrics from final chunk

        if print_response:
            # Thinking header flag
            thinking_started = False
            # Show initial working spinner until first chunk arrives
            first_chunk = True
            status = self.console.status("[cyan]working...", spinner="dots")
            status.start()

            async for chunk in stream:
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

        # Check for JSON tool calls in the accumulated text if no tool_calls object was found
        if not tool_calls and accumulated_text:
            # Some models wrap JSON in markdown, let's strip it
            text_to_parse = accumulated_text.strip()
            if text_to_parse.startswith("```json"):
                text_to_parse = text_to_parse[7:]
                if text_to_parse.endswith("```"):
                    text_to_parse = text_to_parse[:-3]
                text_to_parse = text_to_parse.strip()

            # Find the start and end of the JSON object/array
            json_start = -1
            first_brace = text_to_parse.find('{')
            first_bracket = text_to_parse.find('[')

            if first_brace == -1:
                json_start = first_bracket
            elif first_bracket == -1:
                json_start = first_brace
            else:
                json_start = min(first_brace, first_bracket)

            if json_start != -1:
                json_end = -1
                last_brace = text_to_parse.rfind('}')
                last_bracket = text_to_parse.rfind(']')
                json_end = max(last_brace, last_bracket)

                if json_end > json_start:
                    json_str = text_to_parse[json_start:json_end+1]
                    try:
                        parsed_json = json.loads(json_str)
                        
                        potential_tool_calls = []
                        if isinstance(parsed_json, list):
                            potential_tool_calls = parsed_json
                        elif isinstance(parsed_json, dict):
                            # Some models wrap the call in a 'tool_calls' key
                            if 'tool_calls' in parsed_json and isinstance(parsed_json['tool_calls'], list):
                                potential_tool_calls = parsed_json['tool_calls']
                            else:
                                potential_tool_calls = [parsed_json]

                        for tc_json in potential_tool_calls:
                            # Case 1: Standard OpenAI/Ollama format {'function': {'name': ..., 'arguments': ...}}
                            if (isinstance(tc_json, dict) and 'function' in tc_json and 
                                isinstance(tc_json['function'], dict) and 'name' in tc_json['function'] and 
                                'arguments' in tc_json['function']):
                                
                                tool_calls.append(Message.ToolCall(
                                    function=Message.ToolCall.Function(
                                        name=tc_json['function']['name'],
                                        arguments=tc_json['function']['arguments']
                                    )
                                ))
                            # Case 2: Flattened format {'name': ..., 'arguments': ...} as seen from qwen2.5
                            elif (isinstance(tc_json, dict) and 'name' in tc_json and 'arguments' in tc_json):
                                tool_calls.append(Message.ToolCall(
                                    function=Message.ToolCall.Function(
                                        name=tc_json['name'],
                                        arguments=tc_json['arguments']
                                    )
                                ))
                        
                        if tool_calls:
                            accumulated_text = "" # Clear text if we have tool calls

                    except json.JSONDecodeError:
                        pass # Not a valid JSON, treat as text

        return accumulated_text, tool_calls, metrics
