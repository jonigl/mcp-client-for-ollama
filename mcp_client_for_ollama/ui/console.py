"""Console UI base for MCP Client for Ollama.

This module provides the base console UI functionality used throughout the application.
"""

import os
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

class ConsoleUI:
    """Base class for console UI components.
    
    This class provides common UI functionality used across the application,
    including console clearing, styling, and user input handling.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize ConsoleUI.
        
        Args:
            console: Rich console instance (optional)
        """
        self.console = console or Console()
        self.prompt_session = PromptSession()
        self.prompt_style = Style.from_dict({
            'prompt': 'ansibrightyellow bold',
        })
        
    def clear_console(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    async def get_user_input(self, prompt_text: str = "Input") -> str:
        """Get user input with full keyboard navigation support.
        
        Args:
            prompt_text: Text to display at the prompt
            
        Returns:
            str: User input text
        """
        try:
            user_input = await self.prompt_session.prompt_async(
                f"{prompt_text}: ",
                style=self.prompt_style
            )
            return user_input
        except KeyboardInterrupt:
            return "quit"
        except EOFError:
            return "quit"
            
    def display_panel(self, content, title=None, border_style="green", expand=False):
        """Display content in a panel.
        
        Args:
            content: Panel content (can be string or Text)
            title: Panel title (optional)
            border_style: Color for panel border
            expand: Whether panel should expand to fill width
        """
        if isinstance(content, str):
            content = Text.from_markup(content)
        self.console.print(Panel(content, title=title, border_style=border_style, expand=expand))
