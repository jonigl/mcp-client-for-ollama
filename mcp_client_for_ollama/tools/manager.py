"""Tool management for MCP Client for Ollama.

This module handles enabling, disabling, and selecting tools from MCP servers.
"""

from typing import Dict, List, Any, Optional
from mcp import Tool
from rich.console import Console

class ToolManager:
    """Manages MCP tools.
    
    This class handles enabling and disabling tools, selecting tools through
    an interactive interface, and organizing tools by server.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the ToolManager.
        
        Args:
            console: Rich console for output (optional)
        """
        self.console = console or Console()
        self.available_tools = []
        self.enabled_tools = {}
        
    def select_tools(self):
        """Interactive interface for enabling/disabling tools."""
        pass
    
    def enable_all_tools(self):
        """Enable all available tools."""
        for tool in self.available_tools:
            self.enabled_tools[tool.name] = True
    
    def disable_all_tools(self):
        """Disable all available tools."""
        for tool in self.available_tools:
            self.enabled_tools[tool.name] = False
    
    def display_available_tools(self):
        """Display available tools with their enabled/disabled status."""
        pass
