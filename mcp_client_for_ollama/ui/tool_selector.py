"""Tool selection UI for MCP Client for Ollama.

This module provides the interface for enabling/disabling MCP tools.
"""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.table import Table
from mcp import Tool

from .console import ConsoleUI

class ToolSelectorView(ConsoleUI):
    """Tool selection interface.
    
    This class provides an interactive interface for enabling and disabling
    tools from the connected MCP servers.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ToolSelectorView.
        
        Args:
            console: Rich console for output (optional)
        """
        super().__init__(console)
        
    def display_tool_selection(self, tools: List[Tool], enabled_tools: Dict[str, bool], by_server=False):
        """Display the tool selection interface.
        
        Args:
            tools: List of available tools
            enabled_tools: Dictionary mapping tool names to enabled status
            by_server: Whether to group tools by server
        """
        # Clear console for a clean interface
        self.clear_console()
        
        # Display tool selection interface
        self.console.print(Panel(
            Text.from_markup("[bold]Tool Selection[/bold]", justify="center"), 
            expand=True, 
            border_style="green"
        ))
        
        if by_server:
            # Group tools by server
            tools_by_server = {}
            for tool in tools:
                server = getattr(tool, "server_id", "Unknown")
                if server not in tools_by_server:
                    tools_by_server[server] = []
                tools_by_server[server].append(tool)
                
            # Display tools grouped by server
            for server, server_tools in tools_by_server.items():
                self.console.print(Panel(f"[bold]Server: {server}[/bold]", border_style="blue", expand=False))
                self._display_tool_list(server_tools, enabled_tools)
                self.console.print()
        else:
            # Display all tools in a single list
            self._display_tool_list(tools, enabled_tools)
            
        # Show the command panel
        self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
        self.console.print("• Enter [bold magenta]number[/bold magenta] to toggle a tool")
        self.console.print("• [bold]a[/bold] or [bold]all[/bold] - Enable all tools")
        self.console.print("• [bold]n[/bold] or [bold]none[/bold] - Disable all tools")
        self.console.print("• [bold]g[/bold] or [bold]group[/bold] - Toggle grouping by server")
        self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save tool selection and return")
        self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
        
    def _display_tool_list(self, tools: List[Tool], enabled_tools: Dict[str, bool]):
        """Display a list of tools with their enabled status.
        
        Args:
            tools: List of tools to display
            enabled_tools: Dictionary mapping tool names to enabled status
        """
        # Create a table for tools
        table = Table(show_header=True, expand=True)
        table.add_column("#", style="cyan", no_wrap=True, justify="right")
        table.add_column("Enabled", style="green", no_wrap=True)
        table.add_column("Tool", style="blue")
        table.add_column("Description")
        
        # Add each tool to the table
        for i, tool in enumerate(tools):
            tool_name = tool.name
            enabled = enabled_tools.get(tool_name, False)
            status = "[green]✓[/green]" if enabled else "[red]✗[/red]"
            description = getattr(tool, "description", "No description available")
            
            table.add_row(
                str(i + 1),
                status,
                tool_name,
                description[:50] + ("..." if len(description) > 50 else "")
            )
            
        self.console.print(table)
        
    def get_selection(self) -> str:
        """Get user's tool selection.
        
        Returns:
            str: User's selection input
        """
        return Prompt.ask("> ").strip().lower()
        
    def display_enabled_tools(self, tools: List[Tool], enabled_tools: Dict[str, bool]):
        """Display a summary of enabled tools.
        
        Args:
            tools: List of all available tools
            enabled_tools: Dictionary mapping tool names to enabled status
        """
        enabled_count = sum(1 for tool in tools if enabled_tools.get(tool.name, False))
        total_count = len(tools)
        
        self.console.print(Panel(
            f"[bold blue]Enabled tools:[/bold blue] [green]{enabled_count}[/green]/[cyan]{total_count}[/cyan]", 
            border_style="blue", 
            expand=False
        ))
