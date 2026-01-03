"""Server connection management for MCP Client for Ollama.

This module handles connections to one or more MCP servers, including setup,
initialization, and communication.
"""

import os
import shutil
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from mcp import ClientSession, Tool
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from .discovery import process_server_paths, process_server_urls, parse_server_configs, auto_discover_servers
from ..utils.constants import MCP_PROTOCOL_VERSION
from ..utils.connection import check_url_connectivity

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
        self.session_ids = {}  # Dict to store session IDs for HTTP connections
        self.prompts_by_server = {}  # Dict to store prompts grouped by server

    async def connect_to_servers(self, server_paths=None, server_urls=None, config_path=None, auto_discovery=False) -> Tuple[dict, list, dict, dict]:
        """Connect to one or more MCP servers

        Args:
            server_paths: List of paths to server scripts (.py or .js)
            server_urls: List of URLs for SSE or Streamable HTTP servers
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers

        Returns:
            Tuple of (sessions, available_tools, enabled_tools, prompts_by_server)
        """
        all_servers = []

        # Process server paths
        if server_paths:
            script_servers = process_server_paths(server_paths)
            for server in script_servers:
                self.console.print(f"[cyan]Found server script: {server['path']}[/cyan]")
            all_servers.extend(script_servers)

        # Process server URLs
        if server_urls:
            url_servers = process_server_urls(server_urls)
            for server in url_servers:
                self.console.print(f"[cyan]Found server URL: {server['url']} (type: {server['type']})[/cyan]")
            all_servers.extend(url_servers)

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

        # Check all servers url connectivity
        servers_to_connect = []
        skipped_servers = []
        for server in all_servers:
            if server.get("type") in ["sse", "streamable_http"]:
                if not check_url_connectivity(server.get("url")):
                    skipped_servers.append(server.get("name"))
                    continue
            servers_to_connect.append(server)
        all_servers = servers_to_connect

        if skipped_servers:
            self.console.print(
            f"[red]Skipping servers due to connectivity issues: {', '.join(skipped_servers)}[/red]"
            )
            self.console.print(
            "[yellow]Servers must support HTTP or HTTPS protocols.[/yellow]"
            )

        # Connect to each server
        for server in all_servers:
            await self._connect_to_server(server)

        if not self.sessions:
            self.console.print(Panel(
                "[bold red]Could not connect to any MCP servers![/bold red]\n"
                "Check that server paths exist and are accessible.",
                title="Error", border_style="red", expand=False
            ))

        return self.sessions, self.available_tools, self.enabled_tools, self.prompts_by_server

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
            server_type = server.get("type", "script")
            session = None

            # Connect based on server type
            if server_type == "sse":
                # Connect to SSE server
                url = self._get_url_from_server(server)
                if not url:
                    self.console.print(f"[red]Error: SSE server {server_name} missing URL[/red]")
                    return False

                headers = self._get_headers_from_server(server)

                # Connect using SSE transport
                sse_transport = await self.exit_stack.enter_async_context(sse_client(url, headers=headers))
                read_stream, write_stream = sse_transport
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            elif server_type == "streamable_http":
                # Connect to Streamable HTTP server
                url = self._get_url_from_server(server)
                if not url:
                    self.console.print(f"[red]Error: HTTP server {server_name} missing URL[/red]")
                    return False

                headers = self._get_headers_from_server(server)

                # Use the streamablehttp_client for Streamable HTTP connections
                transport = await self.exit_stack.enter_async_context(
                    streamablehttp_client(url, headers=headers)
                )
                read_stream, write_stream, session_info = transport
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

                # Store session ID if provided
                if hasattr(session_info, 'session_id') and session_info.session_id:
                    self.session_ids[server_name] = session_info.session_id

            elif server_type == "script":
                # Connect to script-based server using STDIO
                server_params = self._create_script_params(server)
                if server_params is None:
                    return False

                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                read_stream, write_stream = stdio_transport
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            else:
                # Connect to config-based server using STDIO
                server_params = self._create_config_params(server)
                if server_params is None:
                    return False

                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                read_stream, write_stream = stdio_transport
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

            # Initialize the session
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

            # Try to get prompts from this server
            server_prompts = []
            try:
                # Attempt to list prompts - will fail gracefully if not supported
                prompts_response = await session.list_prompts()
                server_prompts = prompts_response.prompts if hasattr(prompts_response, 'prompts') else []
                if server_prompts:
                    self.prompts_by_server[server_name] = server_prompts
            except (AttributeError, NotImplementedError, Exception):
                # Server doesn't support prompts or feature not available
                pass

            prompt_count_msg = f" and {len(server_prompts)} prompt(s)" if server_prompts else ""
            self.console.print(f"[green]Successfully connected to {server_name} with {len(server_tools)} tool(s){prompt_count_msg}[/green]")
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

        # Fix and validate directory arguments
        fixed_args, dir_exists, missing_dir = self._fix_directory_args(args)

        if not dir_exists:
            self.console.print(f"[yellow]Warning: Server '{server['name']}' specifies a directory that doesn't exist: {missing_dir}[/yellow]")
            self.console.print(f"[yellow]Skipping server '{server['name']}'[/yellow]")
            return None

        return StdioServerParameters(
            command=command,
            args=fixed_args,
            env=env
        )

    def _fix_directory_args(self, args: List[str]) -> Tuple[List[str], bool, Optional[str]]:
        """Fix common issues with directory arguments and validate directory existence

        Args:
            args: List of command line arguments

        Returns:
            Tuple containing:
            - List of fixed arguments
            - bool indicating if all directories exist
            - Optional[str] containing the first missing directory path if any
        """
        if not args:
            return args, True, None

        fixed_args = args.copy()

        for i, arg in enumerate(fixed_args):
            if arg == "--directory" and i + 1 < len(fixed_args):
                dir_path = fixed_args[i+1]

                # If the path is a file, use its parent directory
                if os.path.isfile(dir_path) and (dir_path.endswith('.py') or dir_path.endswith('.js')):
                    self.console.print(f"[yellow]Warning: Server specifies a file as directory: {dir_path}[/yellow]")
                    self.console.print(f"[green]Automatically fixing to use parent directory instead[/green]")
                    dir_path = os.path.dirname(dir_path) or '.'
                    fixed_args[i+1] = dir_path

                # Check if directory exists
                if not os.path.exists(dir_path):
                    return fixed_args, False, dir_path

        return fixed_args, True, None

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

    def _get_url_from_server(self, server: Dict[str, Any]) -> Optional[str]:
        """Extract URL from server configuration.

        Args:
            server: Server configuration dictionary

        Returns:
            URL string or None if not found
        """
        # Try to get URL directly from server dict
        url = server.get("url")

        # If not there, try the config subdict
        if not url and "config" in server:
            url = server["config"].get("url")

        return url

    def _get_headers_from_server(self, server: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from server configuration.

        Args:
            server: Server configuration dictionary

        Returns:
            Dictionary of headers with lowercase keys
        """
        # Try to get headers directly from server dict
        headers = server.get("headers", {})

        # If not there, try the config subdict
        if not headers and "config" in server:
            headers = server["config"].get("headers", {})

        # Normalize all header names to lowercase per RFC 7230
        headers = {k.lower(): v for k, v in headers.items()}

        # Always add MCP Protocol Version header for HTTP connections
        server_type = server.get("type", "script")
        if server_type in ["sse", "streamable_http"]:
            headers["mcp-protocol-version"] = MCP_PROTOCOL_VERSION

        return headers

    async def disconnect_all_servers(self):
        """Disconnect from all servers and reset state"""
        # Close all existing connections via exit stack
        await self.exit_stack.aclose()

        # Create a new exit stack for future connections
        self.exit_stack = AsyncExitStack()

        # Clear all state
        self.sessions.clear()
        self.available_tools.clear()
        self.enabled_tools.clear()
        self.session_ids.clear()
        self.prompts_by_server.clear()
