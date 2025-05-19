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

class StreamingManager:
    """Manages streaming responses for Ollama API calls"""
    
    def __init__(self, console):
        """Initialize the streaming manager
        
        Args:
            console: Rich console for output
        """
        self.console = console

    def get_table(self, header=True):
        """Create a table for displaying streaming responses
        
        Returns:
            Table: Rich table object
        """
         # Create a table with spinner in first row and content in second
        table = Table.grid(expand=True)
        spinner = Spinner("dots")
        spinner.style = "cyan"  # Make the spinner cyan
        thinking_text = Text("Thinking...", style="cyan")
        if not header:
            spinner = ""
            thinking_text = ""
        # Create inner grid for spinner and text with minimal padding
        header = Table.grid(padding=(0, 1))
        header.add_row(spinner, thinking_text)
        # Add header and content to main table                        
        table.add_row(header)
        return table


    async def process_streaming_response(self, stream, print_response=True):
        """Process a streaming response from Ollama with status spinner and content updates
        
        Args:
            stream: Async iterator of response chunks
            print_response: Flag to control live updating of response text
                
        Returns:
            str: Accumulated response text
            list: Tool calls if any
        """
            
        accumulated_text = ""
        tool_calls = []
        
        # Process the streaming response chunks with live updating markdown
        if print_response:            
            with Live(console=self.console, refresh_per_second=10) as live:
                    table = self.get_table()
                    live.update(table)
                    async for chunk in stream:
                        if hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                            content = chunk.message.content
                            accumulated_text += content
                            table = self.get_table(header=not chunk.done)
                            if len(accumulated_text) > 0:
                                table.add_row(Markdown(accumulated_text))
                            live.update(table)
                        if hasattr(chunk, 'message') and hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
                            # return messages with tool calls
                            for tool in chunk.message.tool_calls:
                                tool_calls.append(tool)
            if len(accumulated_text) > 0:
                self.console.print()
        else:
            async for chunk in stream:
                if hasattr(chunk, 'message') and hasattr(chunk.message, 'content') and chunk.message.content:
                    content = chunk.message.content
                    if content:
                        accumulated_text += content
                    elif hasattr(chunk, 'message') and hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:                        
                        for tool in chunk.message.tool_calls:
                            tool_calls.append(tool)
                                        
        # Return the accumulated text and tool calls
        return accumulated_text, tool_calls
