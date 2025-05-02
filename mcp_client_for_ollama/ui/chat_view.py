"""Chat view UI for MCP Client for Ollama.

This module provides the chat interface for interacting with the model.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .console import ConsoleUI

class ChatView(ConsoleUI):
    """Chat interface for interacting with Ollama.
    
    This class handles displaying chat history, formatting messages,
    and showing tool calls and results.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ChatView.
        
        Args:
            console: Rich console for output (optional)
        """
        super().__init__(console)
        self.chat_history = []
        
    def display_chat_history(self, max_history=3):
        """Display the chat history.
        
        Args:
            max_history: Maximum number of recent conversations to display
        """
        if not self.chat_history:
            return
            
        self.console.print(Panel("[bold]Chat History[/bold]", border_style="blue", expand=False))
        
        # Display the last few conversations
        history_to_show = self.chat_history[-max_history:]
        
        for i, entry in enumerate(history_to_show):
            # Calculate query number
            query_number = len(self.chat_history) - len(history_to_show) + i + 1
            self.console.print(f"[bold green]Query {query_number}:[/bold green]")
            self.console.print(entry["query"].strip())
            self.console.print(f"[bold blue]Response:[/bold blue]")
            self.console.print(Markdown(entry["response"].strip()))
            self.console.print()
            
        if len(self.chat_history) > max_history:
            self.console.print(f"[dim](Showing last {max_history} of {len(self.chat_history)} conversations)[/dim]")
            
    def display_tool_call(self, tool_name: str, tool_args: str):
        """Display information about a tool being called.
        
        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments being passed to the tool
        """
        self.console.print(Panel(f"[bold]Calling tool[/bold]: [blue]{tool_name}[/blue]",
                               subtitle=f"[dim]{tool_args}[/dim]",
                               expand=True))
        self.console.print()
        
    def add_to_history(self, query: str, response: str):
        """Add an interaction to the chat history.
        
        Args:
            query: User query
            response: Model response
        """
        self.chat_history.append({"query": query, "response": response})
        
    def display_help(self):
        """Display help information about available commands."""
        self.console.print(Panel(
            "[yellow]Available Commands:[/yellow]\n\n"
            "[bold cyan]Model and Tools:[/bold cyan]\n"
            "• Type [bold]model[/bold] or [bold]m[/bold] to select a model\n"
            "• Type [bold]tools[/bold] or [bold]t[/bold] to configure tools\n\n"
            
            "[bold cyan]Context Management:[/bold cyan]\n"
            "• Type [bold]context[/bold] or [bold]c[/bold] to toggle context retention\n"
            "• Type [bold]clear[/bold] or [bold]cc[/bold] to clear conversation context\n"
            "• Type [bold]context-info[/bold] or [bold]ci[/bold] to display context info\n\n"
            
            "[bold cyan]Configuration:[/bold cyan]\n"
            "• Type [bold]save-config[/bold] or [bold]sc[/bold] to save the current configuration\n"
            "• Type [bold]load-config[/bold] or [bold]lc[/bold] to load a configuration\n"
            "• Type [bold]reset-config[/bold] or [bold]rc[/bold] to reset configuration to defaults\n\n"
            
            "[bold cyan]Basic Commands:[/bold cyan]\n"
            "• Type [bold]help[/bold] or [bold]h[/bold] to show this help message\n"
            "• Type [bold]clear-screen[/bold] or [bold]cls[/bold] to clear the terminal screen\n"
            "• Type [bold]quit[/bold] or [bold]q[/bold] to exit", 
            title="Help", border_style="yellow", expand=False))
