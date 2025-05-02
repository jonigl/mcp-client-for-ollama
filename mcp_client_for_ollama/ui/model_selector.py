"""Model selection UI for MCP Client for Ollama.

This module provides the interface for selecting Ollama models.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from .console import ConsoleUI

class ModelSelectorView(ConsoleUI):
    """Model selection interface.
    
    This class provides an interactive interface for selecting
    models from the available Ollama models.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ModelSelectorView.
        
        Args:
            console: Rich console for output (optional)
        """
        super().__init__(console)
        
    def display_model_selection(self, models: List[Dict[str, Any]], current_model: str):
        """Display the model selection interface.
        
        Args:
            models: List of available models with metadata
            current_model: Currently selected model name
        """
        # Clear console for a clean interface
        self.clear_console()
        
        # Display model selection interface
        self.console.print(Panel(
            Text.from_markup("[bold]Select a Model[/bold]", justify="center"), 
            expand=True, 
            border_style="green"
        ))
        
        # Sort models by name for easier reading
        sorted_models = sorted(models, key=lambda x: x.get("name", ""))
        
        # Display available models in a numbered list
        self.console.print(Panel("[bold]Available Models[/bold]", border_style="blue", expand=False))
        
        for i, model in enumerate(sorted_models):
            model_name = model.get("name", "Unknown")
            is_current = model_name == current_model
            status = "[green]→[/green] " if is_current else "  "
            
            # Format size if available
            size = model.get("size", 0)
            size_str = f"{size/(1024*1024):.1f} MB" if size else "Unknown size"
            
            # Format date if available
            modified_at = model.get("modified_at", "Unknown date")
            
            self.console.print(f"{i+1}. {status} [bold blue]{model_name}[/bold blue] [dim]({size_str}, {modified_at})[/dim]")
            
        # Show current model with an indicator
        self.console.print(f"\nCurrent model: [bold green]{current_model}[/bold green]\n")
        
        # Show the command panel
        self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
        self.console.print("• Enter [bold magenta]number[/bold magenta] to select a model")
        self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save model selection and return")
        self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
        
    def get_selection(self) -> str:
        """Get user's model selection.
        
        Returns:
            str: User's selection input
        """
        return Prompt.ask("> ").strip().lower()
        
    def display_current_model(self, model: str):
        """Display the currently selected model.
        
        Args:
            model: Current model name
        """
        self.console.print(Panel(
            f"[bold blue]Current model:[/bold blue] [green]{model}[/green]", 
            border_style="blue", 
            expand=False
        ))