"""Welcome screen for MCP Client for Ollama.

This module provides the welcome screen shown when the application starts.
"""

import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from mcp_client_for_ollama import __version__

from .console import ConsoleUI

class WelcomeView(ConsoleUI):
    """Welcome screen UI component.
    
    This class displays the welcome screen when the application starts,
    including versioning information and application status.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the WelcomeView.
        
        Args:
            console: Rich console for output (optional)
        """
        super().__init__(console)
        
    def display_welcome(self, update_available=False, current_version=None, latest_version=None):
        """Display the welcome screen.
        
        Args:
            update_available: Whether a newer version is available
            current_version: Current version of the package
            latest_version: Latest available version of the package
        """
        self.clear_console()
        
        # Application name and banner
        welcome_text = r"""
    ____  __    __    __  _________  _________  _______  _____      _____ __    
   / __ \/ /   / /   /  |/  / ____/ / ____/ / / /  _/ |/ / _ \    / ___// /    
  / / / / /   / /   / /|_/ / /     / __/ / /_/ // //    / ___/   / __ \/ /     
 / /_/ / /___/ /___/ /  / / /___  / /___/ __  // // /|  / / / / / /_/ / /___   
/_____/_____/_____/_/  /_/\____/ /_____/_/ /_/___/_/ |_/_/ |_(_)\____/_____/   
                                                                              
        """
        self.console.print(Text.from_markup(f"[bold blue]{welcome_text}[/bold blue]"))
        
        # Version information
        version_panel = f"[bold cyan]MCP Client for Ollama[/bold cyan] [white]v{__version__}[/white]"
        
        # Update notification if available
        if update_available and current_version and latest_version:
            version_panel += f"\n\n[yellow]Update available![/yellow] v{current_version} → [green]v{latest_version}[/green]"
            version_panel += "\nRun [bold]pip install --upgrade mcp-client-for-ollama[/bold] to update"
        
        self.console.print(Panel(version_panel, border_style="cyan", expand=False))
        self.console.print()
        
        # Interactive usage instructions
        self.console.print(Panel(
            "[white]Type your question or command below. Type [bold]help[/bold] to see available commands.[/white]",
            border_style="green",
            expand=False
        ))
        
    def display_no_ollama_warning(self):
        """Display a warning when Ollama is not running."""
        self.console.print(Panel(
            "[bold red]Ollama is not running![/bold red]\n\n"
            "Please start Ollama first with [bold]ollama serve[/bold] or launch the Ollama application.",
            title="Warning",
            border_style="red",
            expand=False
        ))
        
    def display_server_status(self, connected_servers, total_tools):
        """Display information about connected servers and tools.
        
        Args:
            connected_servers: Number of connected servers
            total_tools: Total number of available tools
        """
        self.console.print(Panel(
            f"[green]✓[/green] Connected to [bold]{connected_servers}[/bold] server(s) with [bold]{total_tools}[/bold] tools available",
            border_style="green",
            expand=False
        ))
