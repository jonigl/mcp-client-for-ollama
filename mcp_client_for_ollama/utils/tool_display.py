"""
Tool display utilities for MCP Client
Handles the formatting and display of tool calls and responses
"""

import json
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from typing import Any


class ToolDisplayManager:
    """Manages the display of tool calls and responses"""

    def __init__(self, console: Console):
        self.console = console

    def _format_json(self, data: Any) -> Syntax:
        """Format data as JSON with syntax highlighting

        Args:
            data: The data to format (always JSON-serializable)

        Returns:
            A Syntax object for JSON display
        """
        if isinstance(data, dict) or isinstance(data, list):
            formatted_json = json.dumps(data, indent=2)
        else:
            # Parse as JSON if it's a string
            parsed_data = json.loads(str(data))
            formatted_json = json.dumps(parsed_data, indent=2)

        # Use Rich Syntax with Monokai theme for JSON
        return Syntax(formatted_json, "json", theme="monokai", line_numbers=False)

    def display_tool_execution(self, tool_name: str, tool_args: Any) -> None:
        """Display the tool execution panel with arguments

        Args:
            tool_name: Name of the tool being executed
            tool_args: Arguments passed to the tool (always JSON-serializable)
        """
        args_display = self._format_json(tool_args)

        # Create the tool execution panel with JSON syntax highlighting
        panel_content = Text.from_markup("[bold]Arguments:[/bold]\n\n")
        panel_renderable = Group(panel_content, args_display)

        self.console.print()  # Add a blank line before the panel
        self.console.print(Panel(
            panel_renderable,
            border_style="blue",
            title=f"[bold cyan]🔧 Executing Tool[/bold cyan] [bold yellow]{tool_name}[/bold yellow]",
            expand=False,
            padding=(1, 2)
        ))

    def display_tool_response(self, tool_name: str, tool_args: Any, tool_response: str) -> None:
        """Display the tool response panel with arguments and response

        Args:
            tool_name: Name of the tool that was executed
            tool_args: Arguments that were passed to the tool (always JSON-serializable)
            tool_response: Response from the tool
        """
        args_display = self._format_json(tool_args)

        # Try to format response as JSON if possible, otherwise display as text
        try:
            response_data = json.loads(tool_response)
            response_display = self._format_json(response_data)

            # Both args and response are formatted - create layout with syntax highlighting
            header_text = Text.from_markup("[bold]Arguments:[/bold]\n\n")
            response_header_text = Text.from_markup("\n[bold]Response:[/bold]\n\n")
            panel_renderable = Group(header_text, args_display, response_header_text, response_display)

        except (json.JSONDecodeError, TypeError, ValueError):
            # Response is not JSON - display as text
            header_text = Text.from_markup("[bold]Arguments:[/bold]\n\n")
            response_text = Text.from_markup(f"\n[bold]Response:[/bold]\n\n[white]{tool_response}[/white]")
            panel_renderable = Group(header_text, args_display, response_text)

        self.console.print()  # Add a blank line before the panel
        self.console.print(Panel(
            panel_renderable,
            border_style="green",
            title=f"[bold green]✅ Tool Response[/bold green] [bold yellow]{tool_name}[/bold yellow]",
            expand=False,
            padding=(1, 2)
        ))
        self.console.print()  # Add a blank line after the panel
