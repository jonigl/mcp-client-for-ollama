"""Server connection management for MCP Client for Ollama.

This module handles connections to one or more MCP servers, including setup, 
initialization, and communication.
"""

import os
import shutil
import asyncio
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

from .discovery import process_server_paths, parse_server_configs, auto_discover_servers

class ServerConnector:
    """Manages connections to one or more MCP servers.
    
    This class handles establishing connections to MCP servers, either from 
    individual script paths or from configuration files, and managing the 
    tools provided by those servers.
    """
    
    def __init__(self, exit_stack: AsyncExitStack, console: Optional[Console] = None):
        """Initialize the ServerConnector.
        
        Args:
            exit_stack: AsyncExitStack to manage server connections
            console: Rich console for output (optional)
        """
        self.exit_stack = exit_stack
        self.console = console or Console()
        self.sessions = {}  # Dict to store multiple sessions
        self.available_tools = []  # List to store all available tools
        self.enabled_tools = {}  # Dict to store tool enabled status
        
    async def connect_to_servers(self, server_paths=None, config_path=None, auto_discovery=False) -> Tuple[dict, list, dict]:
        """Connect to one or more MCP servers
        
        Args:
            server_paths: List of paths to server scripts (.py or .js)
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers
            
        Returns:
            Tuple of (sessions, available_tools, enabled_tools)
        """
        all_servers = []
        
        # Process server paths
        if server_paths:
            script_servers = process_server_paths(server_paths)
            for server in script_servers:
                self.console.print(f"[cyan]Found server script: {server['path']}[/cyan]")
            all_servers.extend(script_servers)
        
        # Process config file
        if config_path:
            try:
                config_servers = parse_server_configs(config_path)
                for server in config_servers:
                    self.console.print(f"[cyan]Found server in config: {server['name']}[/cyan]")
                all_servers.extend(config_servers)
            except Exception as e:
                self.console.print(f"[red]Error loading server configurations: {str(e)}[/red]")
                
        # Auto-discover servers if enabled
        if auto_discovery:
            discovered_servers = auto_discover_servers()
            for server in discovered_servers:
                self.console.print(f"[cyan]Auto-discovered server: {server['name']}[/cyan]")
            all_servers.extend(discovered_servers)
        
        if not all_servers:
            self.console.print(Panel(
                "[yellow]No servers specified or all servers were invalid.[/yellow]\n"
                "The client will continue without tool support.",
                title="Warning", border_style="yellow", expand=False
            ))
            return self.sessions, self.available_tools, self.enabled_tools
            
        # Connect to each server
        for server in all_servers:
            await self._connect_to_server(server)
        
        if not self.sessions:
            self.console.print(Panel(
                "[bold red]Could not connect to any MCP servers![/bold red]\n"
                "Check that server paths exist and are accessible.",
                title="Error", border_style="red", expand=False
            ))
            
        return self.sessions, self.available_tools, self.enabled_tools
    
    async def _connect_to_server(self, server: Dict[str, Any]) -> bool:
        """Connect to a single MCP server
        
        Args:
            server: Server configuration dictionary
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        server_name = server["name"]
        self.console.print(f"[cyan]Connecting to server: {server_name}[/cyan]")
        
        try:
            # Create server parameters based on server type
            if server["type"] == "script":
                server_params = self._create_script_params(server)
                if server_params is None:
                    return False
            else:
                server_params = self._create_config_params(server)
                if server_params is None:
                    return False
            
            # Connect to this server
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await session.initialize()
            
            # Store the session
            self.sessions[server_name] = {
                "session": session,
                "tools": []
            }
            
            # Get tools from this server
            response = await session.list_tools()
            
            # Store and merge tools, prepending server name to avoid conflicts
            server_tools = []
            for tool in response.tools:
                # Create a qualified name for the tool that includes the server
                qualified_name = f"{server_name}.{tool.name}"
                # Clone the tool but update the name
                tool_copy = Tool(
                    name=qualified_name,
                    description=f"[{server_name}] {tool.description}" if hasattr(tool, 'description') else f"Tool from {server_name}",
                    inputSchema=tool.inputSchema,
                    outputSchema=tool.outputSchema if hasattr(tool, 'outputSchema') else None
                )
                server_tools.append(tool_copy)
                self.enabled_tools[qualified_name] = True
            
            self.sessions[server_name]["tools"] = server_tools
            self.available_tools.extend(server_tools)
            
            self.console.print(f"[green]Successfully connected to {server_name} with {len(server_tools)} tools[/green]")
            return True
            
        except FileNotFoundError as e:
            self.console.print(f"[red]Error connecting to {server_name}: File not found - {str(e)}[/red]")
            return False
        except PermissionError:
            self.console.print(f"[red]Error connecting to {server_name}: Permission denied[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Error connecting to {server_name}: {str(e)}[/red]")
            return False
    
    def _create_script_params(self, server: Dict[str, Any]) -> Optional[StdioServerParameters]:
        """Create server parameters for a script-type server
        
        Args:
            server: Server configuration dictionary
            
        Returns:
            StdioServerParameters or None if invalid
        """
        path = server["path"]
        is_python = path.endswith('.py')
        is_js = path.endswith('.js')
        
        if not (is_python or is_js):
            self.console.print(f"[yellow]Warning: Server script {path} must be a .py or .js file. Skipping.[/yellow]")
            return None
            
        command = "python" if is_python else "node"
        
        # Validate the command exists in PATH
        if not shutil.which(command):
            self.console.print(f"[yellow]Warning: Command '{command}' not found in PATH. Skipping server {server['name']}.[/yellow]")
            return None
            
        return StdioServerParameters(
            command=command,
            args=[path],
            env=None
        )
    
    def _create_config_params(self, server: Dict[str, Any]) -> Optional[StdioServerParameters]:
        """Create server parameters for a config-type server
        
        Args:
            server: Server configuration dictionary
            
        Returns:
            StdioServerParameters or None if invalid
        """
        server_config = server["config"]
        command = server_config.get("command")
        
        # Validate the command exists in PATH
        if not command or not shutil.which(command):
            self.console.print(f"[yellow]Warning: Command '{command}' for server '{server['name']}' not found in PATH. Skipping.[/yellow]")
            return None
            
        args = server_config.get("args", [])
        env = server_config.get("env")
        
        # Fix common issues with directory arguments
        fixed_args = self._fix_directory_args(args)
        
        # Check if directory exists with possibly fixed paths
        dir_exists, missing_dir = self.directory_exists(fixed_args)
        
        if not dir_exists:
            self.console.print(f"[yellow]Warning: Server '{server['name']}' specifies a directory that doesn't exist: {missing_dir}[/yellow]")
            self.console.print(f"[yellow]Skipping server '{server['name']}'[/yellow]")
            return None
            
        return StdioServerParameters(
            command=command,
            args=fixed_args,
            env=env
        )
    
    def _fix_directory_args(self, args: List[str]) -> List[str]:
        """Fix common issues with directory arguments
        
        Args:
            args: List of command line arguments
            
        Returns:
            List of fixed arguments
        """
        fixed_args = args.copy()
        
        for i, arg in enumerate(fixed_args):
            if arg == "--directory" and i + 1 < len(fixed_args):
                dir_path = fixed_args[i+1]
                # If the path is a Python file, use its directory instead
                if os.path.isfile(dir_path) and (dir_path.endswith('.py') or dir_path.endswith('.js')):
                    self.console.print(f"[yellow]Warning: Server specifies a file as directory: {dir_path}[/yellow]")
                    self.console.print(f"[green]Automatically fixing to use parent directory instead[/green]")
                    fixed_args[i+1] = os.path.dirname(dir_path) or '.'
        
        return fixed_args
    
    @staticmethod
    def directory_exists(args_list: List[str]) -> Tuple[bool, Optional[str]]:
        """Check if a directory specified in args exists
        
        Looks for a --directory argument followed by a path and checks if that path exists
        
        Args:
            args_list: List of command line arguments
            
        Returns:
            tuple: (directory_exists, directory_path or None)
        """
        if not args_list:
            return True, None
            
        for i, arg in enumerate(args_list):
            if arg == "--directory" and i + 1 < len(args_list):
                directory = args_list[i + 1]
                if os.path.isfile(directory):
                    # If it's a file (like a Python script), use its parent directory
                    directory = os.path.dirname(directory)
                    if os.path.exists(directory):
                        # Modify the args list to use the directory instead of the file
                        args_list[i+1] = directory
                        return True, directory
                    
                if not os.path.exists(directory):
                    return False, directory
        
        return True, None
        
    async def cleanup(self):
        """Clean up resources by closing all server connections"""
        # AsyncExitStack will handle closing all sessions when it's closed
        pass
    
    def get_sessions(self) -> Dict[str, Any]:
        """Get the current server sessions
        
        Returns:
            Dict of server sessions
        """
        return self.sessions
    
    def get_available_tools(self) -> List[Tool]:
        """Get the available tools from all connected servers
        
        Returns:
            List of available tools
        """
        return self.available_tools
    
    def get_enabled_tools(self) -> Dict[str, bool]:
        """Get the current enabled status of all tools
        
        Returns:
            Dict mapping tool names to enabled status
        """
        return self.enabled_tools
    
    def set_tool_status(self, tool_name: str, enabled: bool):
        """Set the enabled status of a specific tool
        
        Args:
            tool_name: Name of the tool to modify
            enabled: Whether the tool should be enabled
        """
        if tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = enabled
    
    def enable_all_tools(self):
        """Enable all available tools"""
        for tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = True
    
    def disable_all_tools(self):
        """Disable all available tools"""
        for tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = False
