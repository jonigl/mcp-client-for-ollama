"""Model management for MCP Client for Ollama.

This module handles listing, selecting, and managing Ollama models.
"""

import aiohttp
from typing import List, Dict, Any, Optional
from rich.console import Console

class ModelManager:
    """Manages Ollama models.
    
    This class handles listing available models from Ollama, checking if
    Ollama is running, and selecting models to use with the client.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ModelManager.
        
        Args:
            console: Rich console for output (optional)
        """
        self.console = console or Console()
        self.model = None
        
    async def check_ollama_running(self) -> bool:
        """Check if Ollama is running by making a request to its API.
        
        Returns:
            bool: True if Ollama is running, False otherwise
        """
        pass
        
    async def list_ollama_models(self) -> List[Dict[str, Any]]:
        """Get a list of available Ollama models.
        
        Returns:
            List[Dict[str, Any]]: List of model objects each with name and other metadata
        """
        pass
        
    async def select_model(self, current_model: str) -> str:
        """Let the user select an Ollama model from the available ones.
        
        Args:
            current_model: The currently selected model
            
        Returns:
            str: The selected model name
        """
        pass