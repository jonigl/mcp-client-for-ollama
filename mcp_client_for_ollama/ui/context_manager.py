"""Context management UI for MCP Client for Ollama.

This module provides the interface for managing conversation context.
"""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from ..utils.constants import TOKEN_COUNT_PER_CHAR

from .console import ConsoleUI

class ContextManagerView(ConsoleUI):
    """Context management interface.
    
    This class provides an interface for managing conversation context,
    including enabling/disabling context retention and displaying context
    statistics.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ContextManagerView.
        
        Args:
            console: Rich console for output (optional)
        """
        super().__init__(console)
        
    def display_context_status(self, retain_context: bool, messages: List[Dict[str, Any]]):
        """Display the current context status.
        
        Args:
            retain_context: Whether context retention is enabled
            messages: List of messages in the current context
        """
        # Calculate approximate context size
        total_length = sum(len(msg.get("content", "")) for msg in messages)
        approx_tokens = int(total_length * TOKEN_COUNT_PER_CHAR)
        
        status = "[green]Enabled[/green]" if retain_context else "[red]Disabled[/red]"
        
        # Display context status in a panel
        self.console.print(Panel(
            f"[bold]Context Retention:[/bold] {status}\n\n"
            f"[bold]Context Size:[/bold] {len(messages)} messages (~{approx_tokens} tokens)",
            title="Context Status",
            border_style="blue",
            expand=False
        ))
        
        if messages and retain_context:
            # Show a preview of the context if it exists and is enabled
            self.console.print(Panel(
                "[bold]Context Preview:[/bold]", 
                border_style="cyan", 
                expand=False
            ))
            
            # Display at most the last 3 messages
            preview_messages = messages[-3:]
            for i, msg in enumerate(preview_messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                # Format based on role
                if role == "user":
                    self.console.print(f"[bold green]User:[/bold green]")
                    self.console.print(content[:100] + ("..." if len(content) > 100 else ""))
                elif role == "assistant":
                    self.console.print(f"[bold blue]Assistant:[/bold blue]")
                    self.console.print(Markdown(content[:100] + ("..." if len(content) > 100 else "")))
                else:
                    self.console.print(f"[bold]{role}:[/bold]")
                    self.console.print(content[:100] + ("..." if len(content) > 100 else ""))
                    
                self.console.print()
                
            if len(messages) > 3:
                self.console.print(f"[dim](Showing last {len(preview_messages)} of {len(messages)} messages)[/dim]")
        
    def display_context_toggle_result(self, retain_context: bool):
        """Display the result of toggling context retention.
        
        Args:
            retain_context: The new context retention status
        """
        status = "[green]enabled[/green]" if retain_context else "[red]disabled[/red]"
        self.console.print(Panel(
            f"Context retention is now {status}.",
            border_style="green" if retain_context else "red",
            expand=False
        ))
        
    def display_context_cleared(self):
        """Display a confirmation message after clearing the context."""
        self.console.print(Panel(
            "[green]Context has been cleared.[/green]",
            border_style="green",
            expand=False
        ))