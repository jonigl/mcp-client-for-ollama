"""Model management for MCP Client for Ollama.

This module handles listing, selecting, and managing Ollama models.
"""

import aiohttp
import dateutil.parser
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

class ModelManager:
    """Manages Ollama models.
    
    This class handles listing available models from Ollama, checking if
    Ollama is running, and selecting models to use with the client.
    """
    
    def __init__(self, console: Optional[Console] = None, default_model: str = "qwen2.5:7b"):
        """Initialize the ModelManager.
        
        Args:
            console: Rich console for output (optional)
            default_model: Default model to use if none is specified
        """
        self.console = console or Console()
        self.model = default_model
        
    async def check_ollama_running(self) -> bool:
        """Check if Ollama is running by making a request to its API.
        
        Returns:
            bool: True if Ollama is running, False otherwise
        """
        try:
            # Try to make a simple request to the Ollama API
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags") as response:
                    if response.status == 200:
                        return True
                    return False
        except Exception:
            return False
            
    async def list_ollama_models(self) -> List[Dict[str, Any]]:
        """Get a list of available Ollama models.
        
        Returns:
            List[Dict[str, Any]]: List of model objects each with name and other metadata
        """
        try:
            # Get models from Ollama API
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        if "models" in data:
                            return data["models"]
                        return []
                    else:
                        self.console.print(f"[red]Error getting models from Ollama API: {response.status}[/red]")
                        return []
        except Exception as e:
            self.console.print(f"[red]Error getting models from Ollama: {str(e)}[/red]")
            return []

    def get_current_model(self) -> str:
        """Get the currently selected model.
        
        Returns:
            str: Name of the current model
        """
        return self.model
        
    def set_model(self, model_name: str) -> None:
        """Set the current model.
        
        Args:
            model_name: Name of the model to set as current
        """
        self.model = model_name
    
    def display_current_model(self) -> None:
        """Display the currently selected model in the console."""
        self.console.print(Panel(f"[bold blue]Current model:[/bold blue] [green]{self.model}[/green]", 
                              border_style="blue", expand=False))
    
    def validate_model_exists(self, model_name: str, models: List[Dict[str, Any]]) -> bool:
        """Check if a model exists in the list of available models.
        
        Args:
            model_name: Name of the model to check
            models: List of available models
            
        Returns:
            bool: True if the model exists, False otherwise
        """
        model_names = [model.get("name", "") for model in models]
        return model_name in model_names
        
    def format_model_display_info(self, model: Dict[str, Any]) -> Tuple[str, str, str]:
        """Format model information for display.
        
        Args:
            model: Model metadata dictionary
            
        Returns:
            Tuple[str, str, str]: Model name, size string, and modified date string
        """
        # Extract model name, trying different fields
        model_name = model.get("name", "Unknown")
        if model_name == "Unknown":
            # Try alternative fields that might contain the name
            for key in ["name", "model", "tag", "id"]:
                if key in model and model[key]:
                    model_name = model[key]
                    break
        
        # Format size if available
        size = model.get("size", 0)
        size_str = f"{size/(1024*1024):.1f} MB" if size else "Unknown size"
        
        # Format the date if available
        modified_at = model.get("modified_at", "Unknown")
        if modified_at != "Unknown":
            try:
                modified_at = dateutil.parser.parse(modified_at).strftime("%Y-%m-%d %H:%M:%S")                                        
            except Exception:
                modified_at = "Unknown date"
                
        return model_name, size_str, modified_at
        
    async def select_model_interactive(self, clear_console_func=None) -> str:
        """Let the user select an Ollama model from the available ones.
        
        Args:
            clear_console_func: Function to clear the console (optional)
            
        Returns:
            str: The selected model name (or the original if canceled)
        """
        # Check if Ollama is running first
        if not await self.check_ollama_running():
            self.console.print(Panel(
                "[bold red]Ollama is not running![/bold red]\n\n"
                "Please start Ollama before trying to list or switch models.\n"
                "You can start Ollama by running the 'ollama serve' command in a terminal.",
                title="Error", border_style="red", expand=False
            ))
            return self.model
        
        # Save the current model in case the user cancels
        original_model = self.model
        # Track currently selected model (which might not be saved yet)
        selected_model = self.model
            
        # Get available models
        with self.console.status("[cyan]Getting available models from Ollama...[/cyan]"):
            models = await self.list_ollama_models()
            
        if not models:
            self.console.print("[yellow]No models available. Try pulling a model with 'ollama pull <model>'[/yellow]")
            return self.model

        # Main model selection loop
        while True:
            # Clear console for a clean interface
            if clear_console_func:
                clear_console_func()
            
            # Display model selection interface
            self.console.print(Panel(Text.from_markup("[bold]Select a Model[/bold]", justify="center"), expand=True, border_style="green"))        
            
            # Sort models by name for easier reading
            models.sort(key=lambda x: x.get("name", ""))
                    
            # Display available models in a numbered list
            self.console.print(Panel("[bold]Available Models[/bold]", border_style="blue", expand=False))
            
            # Display available models
            for i, model in enumerate(models):
                model_name, size_str, modified_at = self.format_model_display_info(model)
                # Check if this model is the currently selected one (not yet saved)
                is_current = model_name == selected_model
                status = "[green]→[/green] " if is_current else "  "
                self.console.print(f"{i+1}. {status} [bold blue]{model_name}[/bold blue] [dim]({size_str}, {modified_at})[/dim]")
                
            # Show current model with an indicator (this is the saved model)
            self.console.print(f"\nCurrent model: [bold green]{self.model}[/bold green]")
            if selected_model != self.model:
                self.console.print(f"Selected model: [bold yellow]{selected_model}[/bold yellow] (not saved yet)")
            self.console.print()
            
            # Show the command panel
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print("• Enter [bold magenta]number[/bold magenta] to select a model")
            self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save model selection and return")
            self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
            
            selection = Prompt.ask("> ")
            selection = selection.strip().lower()
            
            if selection in ['s', 'save']:
                # Save the selected model as current model
                self.model = selected_model
                if clear_console_func:
                    clear_console_func()
                self.console.print("[green]Model selection saved![/green]")
                return self.model
            
            if selection in ['q', 'quit']:
                # Restore original model
                if clear_console_func:
                    clear_console_func()
                self.console.print("[yellow]Model selection cancelled.[/yellow]")
                return original_model
                
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(models):
                    # Update the selected model (but don't save it yet)
                    model_data = models[idx]
                    # Try multiple fields that might contain the model name
                    for key in ["name", "model", "tag", "id"]:
                        if key in model_data and model_data[key]:
                            selected_model = model_data[key]
                            break
                    else:
                        # If we couldn't find a name, inform the user
                        if clear_console_func:
                            clear_console_func()
                        self.console.print("[red]Error: Could not determine the model name from the API response.[/red]")
                else:
                    if clear_console_func:
                        clear_console_func()
                    self.console.print(f"[red]Invalid number: {idx + 1}. Must be between 1 and {len(models)}[/red]")
            except ValueError:
                if clear_console_func:
                    clear_console_func()
                self.console.print("[red]Invalid input. Please enter a number.[/red]")
