import argparse
import asyncio
import json
import os
import shutil
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from mcp_client_for_ollama import __version__
import ollama
from ollama import ChatResponse
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich import print as rprint
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from typing import List, Dict, Any, Tuple
import aiohttp
from datetime import datetime
import dateutil.parser
import re

# Default Claude config file location
DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
# Default config directory and filename for MCP client for Ollama
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/ollmcp")
if not os.path.exists(DEFAULT_CONFIG_DIR):
    os.makedirs(DEFAULT_CONFIG_DIR)

DEFAULT_CONFIG_FILE = "config.json"

class MCPClient:
    def __init__(self, model: str):
        # Initialize session and client objects
        self.sessions = {}  # Dict to store multiple sessions
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient()
        self.model = model
        self.available_tools: List[Tool] = []
        self.enabled_tools: Dict[str, bool] = {}
        self.console = Console()
        self.chat_history = []  # Add chat history list to store interactions
        self.prompt_session = PromptSession()
        self.prompt_style = Style.from_dict({
            'prompt': 'ansibrightyellow bold',
        })
        # Context retention settings
        self.retain_context = True  # By default, retain conversation context        
        self.approx_token_count = 0  # Approximate token count for the conversation
        self.token_count_per_char = 0.25  # Rough approximation of tokens per character
        
    async def check_ollama_running(self) -> bool:
        """Check if Ollama is running by making a request to its API
        
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
        """Get a list of available Ollama models
        
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
            
    def display_current_model(self):
        """Display the currently selected model"""
        self.console.print(Panel(f"[bold blue]Current model:[/bold blue] [green]{self.model}[/green]", 
                               border_style="blue", expand=False))
                               
    async def select_model(self):
        """Let the user select an Ollama model from the available ones"""
        # Check if Ollama is running first
        if not await self.check_ollama_running():
            self.console.print(Panel(
                "[bold red]Ollama is not running![/bold red]\n\n"
                "Please start Ollama before trying to list or switch models.\n"
                "You can start Ollama by running the 'ollama serve' command in a terminal.",
                title="Error", border_style="red", expand=False
            ))
            return
        
        # Save the current model in case the user cancels
        original_model = self.model
            
        # Get available models
        with self.console.status("[cyan]Getting available models from Ollama...[/cyan]"):
            models = await self.list_ollama_models()
            
        if not models:
            self.console.print("[yellow]No models available. Try pulling a model with 'ollama pull <model>'[/yellow]")
            return
            
        # Clear console for a clean interface
        self.clear_console()
        
        # Display model selection interface
        self.console.print(Panel(Text.from_markup("[bold]Select a Model[/bold]", justify="center"), expand=True, border_style="green"))        
        
        # Sort models by name for easier reading
        models.sort(key=lambda x: x.get("name", ""))
                
        # Display available models in a numbered list
        self.console.print(Panel("[bold]Available Models[/bold]", border_style="blue", expand=False))        
        # Display available models
        for i, model in enumerate(models):
            model_name = model.get("name", "Unknown")
            is_current = model_name == self.model
            status = "[green]→[/green] " if is_current else "  "
            size = model.get("size", 0)
            size_str = f"{size/(1024*1024):.1f} MB" if size else "Unknown size"
            
            # Format the date if available
            modified_at = model.get("modified_at", "Unknown")
            if modified_at != "Unknown":
                try:
                    modified_at = dateutil.parser.parse(modified_at).strftime("%Y-%m-%d %H:%M:%S")                                        
                except Exception as e:
                    self.console.print(f"[red]Error parsing date: {str(e)}[/red]")
                    modified_at = "Unknown date"
            
            # Debug: Print raw model data if name is not found
            if model_name == "Unknown":
                self.console.print(f"[dim]Debug - Model data: {model}[/dim]")
                # Try alternative fields that might contain the name
                for key in ["name", "model", "tag", "id"]:
                    if key in model and model[key]:
                        model_name = model[key]
                        break
            
            self.console.print(f"{i+1}. {status} [bold blue]{model_name}[/bold blue] [dim]({size_str}, {modified_at})[/dim]")
        # Show current model with an indicator
        self.console.print(f"\nCurrent model: [bold green]{self.model}[/bold green]\n")
        # Show the command panel
        self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
        self.console.print("• Enter [bold magenta]number[/bold magenta] to select a model")
        self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save model selection and return")
        self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
        
        selection = Prompt.ask("> ")
        selection = selection.strip().lower()
        
        if selection in ['s', 'save']:
            # Keep the current model selection
            self.clear_console()
            self.console.print("[green]Model selection saved![/green]")
            # Display available tools
            self.display_available_tools()
            # Display the current model
            self.display_current_model()
            # Display chat history before returning to chat interface
            self._display_chat_history()
            return
        
        if selection in ['q', 'quit']:
            # Restore original model
            self.model = original_model
            self.clear_console()
            self.console.print("[yellow]Model selection cancelled.[/yellow]")
            # Display available tools
            self.display_available_tools()
            # Display the current model
            self.display_current_model()
            # Display chat history before returning to chat interface
            self._display_chat_history()
            return
            
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(models):
                # Update the model
                model_data = models[idx]
                # Try multiple fields that might contain the model name
                for key in ["name", "model", "tag", "id"]:
                    if key in model_data and model_data[key]:
                        new_model = model_data[key]
                        old_model = self.model
                        self.model = new_model
                        self.clear_console()
                        self.console.print(f"[green]Model changed from [bold]{old_model}[/bold] to [bold]{new_model}[/bold]![/green]")
                        # Show a message that changes need to be saved
                        self.console.print("[yellow]Use 's' to save this selection or 'q' to cancel[/yellow]")
                        return await self.select_model()  # Return to model selection to save/cancel
                
                # If we couldn't find a name, inform the user
                self.clear_console()
                self.console.print("[red]Error: Could not determine the model name from the API response.[/red]")
                # Return to model selection
                return await self.select_model()
            else:
                self.clear_console()
                self.console.print(f"[red]Invalid number: {idx + 1}. Must be between 1 and {len(models)}[/red]")
                # Return to model selection
                return await self.select_model()
        except ValueError:
            self.clear_console()
            self.console.print("[red]Invalid input. Please enter a number.[/red]")
            # Return to model selection
            return await self.select_model()

    def clear_console(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_available_tools(self):
        """Display available tools with their enabled/disabled status"""
        
        # Create a list of styled tool names
        tool_texts = []
        enabled_count = 0
        for tool in self.available_tools:
            is_enabled = self.enabled_tools.get(tool.name, True)
            if is_enabled:
                enabled_count += 1
            status = "[green]✓[/green]" if is_enabled else "[red]✗[/red]"
            tool_texts.append(f"{status} {tool.name}")
        
        # Display tools in columns for better readability
        if tool_texts:
            columns = Columns(tool_texts, equal=True, expand=True)
            subtitle = f"{enabled_count}/{len(self.available_tools)} tools enabled"
            self.console.print(Panel(columns, title="Available Tools", subtitle=subtitle, border_style="green"))
        else:
            self.console.print("[yellow]No tools available from the server[/yellow]")

    @staticmethod
    def load_server_config(config_path: str) -> Dict[str, Any]:
        """Load and parse a server configuration file
        
        Args:
            config_path: Path to the JSON config file
            
        Returns:
            Dictionary containing server configurations
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('mcpServers', {})
        except Exception as e:
            raise ValueError(f"Error loading server config from {config_path}: {str(e)}")

    @staticmethod
    def directory_exists(args_list):
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

    async def connect_to_servers(self, server_paths=None, config_path=None):
        """Connect to one or more MCP servers
        
        Args:
            server_paths: List of paths to server scripts (.py or .js)
            config_path: Path to JSON config file with server configurations
        """
        all_servers = []
        
        # Add individual server paths if provided
        if server_paths:
            if isinstance(server_paths, str):
                server_paths = [server_paths]
                
            for path in server_paths:
                # Check if the path exists and is a file
                if not os.path.exists(path):
                    self.console.print(f"[yellow]Warning: Server path '{path}' does not exist. Skipping.[/yellow]")
                    continue
                    
                if not os.path.isfile(path):
                    self.console.print(f"[yellow]Warning: Server path '{path}' is not a file. Skipping.[/yellow]")
                    continue
                
                all_servers.append({
                    "type": "script",
                    "path": path,
                    "name": os.path.basename(path).split('.')[0]  # Use filename without extension as name
                })
        
        # Add servers from config file if provided
        if config_path:
            try:
                server_configs = self.load_server_config(config_path)
                for name, config in server_configs.items():
                    # Skip disabled servers
                    if config.get('disabled', False):
                        continue
                    
                    # Check if required directory exists
                    args = config.get("args", [])
                    
                    # Fix common issues with directory arguments
                    for i, arg in enumerate(args):
                        if arg == "--directory" and i + 1 < len(args):
                            dir_path = args[i+1]
                            # If the path is a Python file, use its directory instead
                            if os.path.isfile(dir_path) and (dir_path.endswith('.py') or dir_path.endswith('.js')):
                                self.console.print(f"[yellow]Warning: Server '{name}' specifies a file as directory: {dir_path}[/yellow]")
                                self.console.print(f"[green]Automatically fixing to use parent directory instead[/green]")
                                args[i+1] = os.path.dirname(dir_path) or '.'
                    
                    # Now check if directory exists with possibly fixed paths
                    dir_exists, missing_dir = self.directory_exists(args)
                    
                    if not dir_exists:
                        self.console.print(f"[yellow]Warning: Server '{name}' specifies a directory that doesn't exist: {missing_dir}[/yellow]")
                        self.console.print(f"[yellow]Skipping server '{name}'[/yellow]")
                        continue
                        
                    all_servers.append({
                        "type": "config",
                        "name": name,
                        "config": config
                    })
            except Exception as e:
                self.console.print(f"[red]Error loading server configurations: {str(e)}[/red]")
        
        if not all_servers:
            self.console.print("[yellow]No servers specified or all servers were invalid. The client will continue without tool support.[/yellow]")
            return
            
        # Connect to each server
        for server in all_servers:
            server_name = server["name"]
            self.console.print(f"[cyan]Connecting to server: {server_name}[/cyan]")
            
            try:
                if server["type"] == "script":
                    # Handle direct script path
                    path = server["path"]
                    is_python = path.endswith('.py')
                    is_js = path.endswith('.js')
                    
                    if not (is_python or is_js):
                        self.console.print(f"[yellow]Warning: Server script {path} must be a .py or .js file. Skipping.[/yellow]")
                        continue
                        
                    command = "python" if is_python else "node"
                    server_params = StdioServerParameters(
                        command=command,
                        args=[path],
                        env=None
                    )
                else:
                    # Handle config-based server
                    server_config = server["config"]
                    command = server_config.get("command")
                    
                    # Validate the command exists in PATH
                    if not shutil.which(command):
                        self.console.print(f"[yellow]Warning: Command '{command}' for server '{server_name}' not found in PATH. Skipping.[/yellow]")
                        continue
                        
                    args = server_config.get("args", [])
                    env = server_config.get("env")
                    
                    server_params = StdioServerParameters(
                        command=command,
                        args=args,
                        env=env
                    )
                
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
                
            except FileNotFoundError as e:
                self.console.print(f"[red]Error connecting to {server_name}: File not found - {str(e)}[/red]")
            except PermissionError:
                self.console.print(f"[red]Error connecting to {server_name}: Permission denied[/red]")
            except Exception as e:
                self.console.print(f"[red]Error connecting to {server_name}: {str(e)}[/red]")
        
        if not self.sessions:
            self.console.print("[bold red]Warning: Could not connect to any MCP servers![/bold red]")
            if config_path:
                self.console.print(f"[yellow]Check if paths in {config_path} exist and are accessible[/yellow]")

    async def connect_to_server(self, server_script_path: str):
        """Connect to a single MCP server (legacy support)"""
        await self.connect_to_servers([server_script_path])

    def select_tools(self):
        """Let the user select which tools to enable using interactive prompts with server-based grouping"""
        # Save the original tool states in case the user cancels
        original_states = self.enabled_tools.copy()
        show_descriptions = False  # Default: don't show descriptions
        result_message = None      # Store the result message to display in a panel
        result_style = "green"     # Style for the result message panel
        
        # Group tools by server
        servers = {}
        for tool in self.available_tools:
            server_name, tool_name = tool.name.split('.', 1) if '.' in tool.name else ("default", tool.name)
            if server_name not in servers:
                servers[server_name] = []
            servers[server_name].append(tool)
        
        # Sort servers by name for consistent display
        sorted_servers = sorted(servers.items(), key=lambda x: x[0])
        
        # Clear the console to create a "new console" effect
        self.clear_console()
        
        while True:
            # Show the tool selection interface
            self.console.print(Panel(Text.from_markup("[bold]Tool Selection[/bold]", justify="center"), expand=True, border_style="green"))
            
            # Display the server groups and their tools
            self.console.print(Panel("[bold]Available Servers and Tools[/bold]", border_style="blue", expand=False))
            
            tool_index = 1  # Global tool index across all servers
            
            # Create a mapping of display indices to tools for accurate selection
            index_to_tool = {}
            
            # Calculate and display server stats and tools
            for server_idx, (server_name, server_tools) in enumerate(sorted_servers):
                enabled_count = sum(1 for tool in server_tools if self.enabled_tools[tool.name])
                total_count = len(server_tools)
                
                # Determine server status indicator
                if enabled_count == total_count:
                    server_status = "[green]✓[/green]"  # All enabled
                elif enabled_count == 0:
                    server_status = "[red]✗[/red]"      # None enabled
                else:
                    server_status = "[yellow]~[/yellow]"  # Some enabled
                
                # Create panel title with server number, status and name
                panel_title = f"[bold orange3]S{server_idx+1}. {server_status} {server_name}[/bold orange3]"
                # Create panel subtitle with tools count
                panel_subtitle = f"[green]{enabled_count}/{total_count} tools enabled[/green]"
                
                # Different display mode based on whether descriptions are shown
                if show_descriptions:
                    # Simple list format for when descriptions are shown
                    tool_list = []
                    for tool in server_tools:
                        status = "[green]✓[/green]" if self.enabled_tools[tool.name] else "[red]✗[/red]"
                        tool_text = f"[magenta]{tool_index}[/magenta]. {status} {tool.name}"
                        
                        # Add description if available
                        if hasattr(tool, 'description') and tool.description:
                            # Indent description for better readability
                            description = f"\n      {tool.description}"
                            tool_text += description
                            
                        tool_list.append(tool_text)
                        
                        # Store the mapping from display index to tool
                        index_to_tool[tool_index] = tool
                        tool_index += 1
                    
                    # Join tool texts with newlines
                    panel_content = "\n".join(tool_list)
                    self.console.print(Panel(panel_content, padding=(1,1), title=panel_title, 
                                          subtitle=panel_subtitle, border_style="blue", 
                                          title_align="left", subtitle_align="right"))
                else:
                    # Original columns format for when descriptions are hidden
                    # Display individual tools for this server in columns
                    server_tool_texts = []
                    for tool in server_tools:
                        status = "[green]✓[/green]" if self.enabled_tools[tool.name] else "[red]✗[/red]"
                        tool_text = f"[magenta]{tool_index}[/magenta]. {status} {tool.name}"
                        
                        # Store the mapping from display index to tool
                        index_to_tool[tool_index] = tool
                        tool_index += 1
                        
                        server_tool_texts.append(tool_text)
                    
                    # Display tools in columns inside a panel if there are any
                    if server_tool_texts:
                        columns = Columns(server_tool_texts, padding=(0, 2), equal=False, expand=False)
                        self.console.print(Panel(columns, padding=(1,1), title=panel_title, subtitle=panel_subtitle, border_style="blue", title_align="left", subtitle_align="right"))
                
                self.console.print()  # Add space between servers
            
            # Display the result message if there is one
            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None  # Clear the message after displaying it
                                
            # Display the command panel
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print(f"• Enter [bold magenta]numbers[/bold magenta][bold yellow] separated by commas or ranges[/bold yellow] to toggle tools (e.g. [bold]1,3,5-8[/bold])")
            self.console.print(f"• Enter [bold orange3]S + number[/bold orange3] to toggle all tools in a server (e.g. [bold]S1[/bold] or [bold]s2[/bold])")
            self.console.print("• [bold]a[/bold] or [bold]all[/bold] - Enable all tools")
            self.console.print("• [bold]n[/bold] or [bold]none[/bold] - Disable all tools")
            self.console.print(f"• [bold]d[/bold] or [bold]desc[/bold] - {'Hide' if show_descriptions else 'Show'} descriptions")
            self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save changes and return")
            self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")
            
            selection = Prompt.ask("> ")
            selection = selection.strip().lower()
            
            if selection in ['s', 'save']:
                self.clear_console()
                # Instead of printing directly, display the chat history and tools
                self._display_chat_history()
                self.display_available_tools()      
                self.display_current_model()
                return
            
            if selection in ['q', 'quit']:
                # Restore original tool states
                self.enabled_tools = original_states.copy()
                self.clear_console()
                # Instead of printing directly, display the chat history and tools
                self._display_chat_history()
                self.display_available_tools()
                self.display_current_model()
                return
            
            if selection in ['a', 'all']:
                for tool in self.available_tools:
                    self.enabled_tools[tool.name] = True
                self.clear_console()
                result_message = "[green]All tools enabled![/green]"                
                continue
            
            if selection in ['n', 'none']:
                for tool in self.available_tools:
                    self.enabled_tools[tool.name] = False
                self.clear_console()
                result_message = "[yellow]All tools disabled![/yellow]"                
                continue
                
            if selection in ['d', 'desc']:
                show_descriptions = not show_descriptions
                self.clear_console()
                status = "shown" if show_descriptions else "hidden"
                result_message = f"[blue]Tool descriptions {status}![/blue]"                
                continue
            
            # Check for server toggle (S1, S2, etc.)
            if selection.startswith('s') and len(selection) > 1 and selection[1:].isdigit():
                server_idx = int(selection[1:]) - 1
                if 0 <= server_idx < len(sorted_servers):
                    server_name, server_tools = sorted_servers[server_idx]
                    
                    # Check if all tools in this server are currently enabled
                    all_enabled = all(self.enabled_tools[tool.name] for tool in server_tools)
                    
                    # Toggle accordingly: if all are enabled, disable all; otherwise enable all
                    new_state = not all_enabled
                    for tool in server_tools:
                        self.enabled_tools[tool.name] = new_state
                    
                    self.clear_console()
                    status = "enabled" if new_state else "disabled"
                    result_message = f"[{'green' if new_state else 'yellow'}]All tools in server '{server_name}' {status}![/{'green' if new_state else 'yellow'}]"                    
                else:
                    self.clear_console()
                    result_message = f"[red]Invalid server number: S{server_idx+1}. Must be between S1 and S{len(sorted_servers)}[/red]"
                    result_style = "red"
                continue
            
            # Process individual tool selections and ranges
            try:
                valid_toggle = False
                
                # Split the input by commas to handle multiple selections
                parts = [part.strip() for part in selection.split(',') if part.strip()]
                selections = []
                
                for part in parts:
                    # Check if this part is a range (e.g., "5-8")
                    if '-' in part:
                        try:
                            start, end = map(int, part.split('-', 1))
                            selections.extend(range(start, end + 1))
                        except ValueError:
                            self.console.print(f"[red]Invalid range: {part}[/red]")
                    else:
                        # Otherwise, treat as a single number
                        try:
                            selections.append(int(part))
                        except ValueError:
                            self.console.print(f"[red]Invalid selection: {part}[/red]")
                
                # Process the selections using our accurate mapping
                toggled_tools_count = 0
                invalid_indices = []
                
                for idx in selections:
                    if idx in index_to_tool:
                        tool = index_to_tool[idx]
                        self.enabled_tools[tool.name] = not self.enabled_tools[tool.name]
                        valid_toggle = True
                        toggled_tools_count += 1
                    else:
                        invalid_indices.append(idx)
                
                self.clear_console()
                if valid_toggle:
                    result_message = f"[green]Successfully toggled {toggled_tools_count} tool{'s' if toggled_tools_count != 1 else ''}![/green]"
                    if invalid_indices:
                        result_message += f"\n[yellow]Warning: Invalid indices ignored: {', '.join(map(str, invalid_indices))}[/yellow]"
                else:
                    result_message = "[yellow]No valid tool numbers provided.[/yellow]"
                    result_style = "yellow"
            
            except ValueError:
                self.clear_console()
                result_message = "[red]Invalid input. Please enter numbers, ranges, or server designators.[/red]"
                result_style = "red"

    def _display_chat_history(self):
        """Display chat history when returning to the main chat interface"""
        if self.chat_history:
            self.console.print(Panel("[bold]Chat History[/bold]", border_style="blue", expand=False))
            
            # Display the last few conversations (limit to keep the interface clean)
            max_history = 3
            history_to_show = self.chat_history[-max_history:]
            
            for i, entry in enumerate(history_to_show):
                # Calculate query number starting from 1 for the first query
                query_number = len(self.chat_history) - len(history_to_show) + i + 1
                self.console.print(f"[bold green]Query {query_number}:[/bold green]")
                self.console.print(Text(entry["query"].strip(), style="green"))
                self.console.print(f"[bold blue]Response:[/bold blue]")
                self.console.print(Markdown(entry["response"].strip()))
                self.console.print()
                
            if len(self.chat_history) > max_history:
                self.console.print(f"[dim](Showing last {max_history} of {len(self.chat_history)} conversations)[/dim]")

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        # Create base message with current query
        current_message = {
            "role": "user",
            "content": query
        }
        
        # Build messages array based on context retention setting
        if self.retain_context and self.chat_history:
            # Include previous messages for context
            messages = []
            for entry in self.chat_history:
                # Add user message
                messages.append({
                    "role": "user",
                    "content": entry["query"]
                })
                # Add assistant response 
                messages.append({
                    "role": "assistant",
                    "content": entry["response"]
                })
            # Add the current query
            messages.append(current_message)
        else:
            # No context retention - just use current query
            messages = [current_message]

        # Filter tools based on user selection
        enabled_tool_objects = [tool for tool in self.available_tools if self.enabled_tools.get(tool.name, False)]
        
        if not enabled_tool_objects:
            self.console.print("[yellow]Warning: No tools are enabled. Model will respond without tool access.[/yellow]")
        
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in enabled_tool_objects]        

        # Initial Ollama API call
        with self.console.status("[cyan]Thinking...[/cyan]"):
            response: ChatResponse = await self.ollama.chat(
                model=self.model,
                messages=messages,
                tools=available_tools,
                options={"num_predict": 1000}
            )

        # Process response and handle tool calls
        final_text = []
        
        if hasattr(response.message, 'content') and response.message.content:
            final_text.append(response.message.content)            

        elif response.message.tool_calls:
            for tool in response.message.tool_calls:
                tool_name = tool.function.name
                tool_args = tool.function.arguments

                # Parse server name and actual tool name from the qualified name
                server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)
                
                if not server_name or server_name not in self.sessions:
                    self.console.print(f"[red]Error: Unknown server for tool {tool_name}[/red]")
                    continue
                
                # Execute tool call
                self.console.print(Panel(f"[bold]Calling tool[/bold]: [blue]{tool_name}[/blue]", 
                                       subtitle=f"[dim]{tool_args}[/dim]", 
                                       expand=True))
                self.console.print()
                
                with self.console.status(f"[cyan]Running {tool_name}...[/cyan]"):
                    result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
                
                self.console.print()
                
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "name": tool_name
                })            

                # Get next response from Ollama with the tool results
                with self.console.status("[cyan]Processing results...[/cyan]"):
                    response = await self.ollama.chat(
                        model=self.model,
                        messages=messages,
                        tools=available_tools,
                    )

                self.console.print() 
                final_text.append(response.message.content)

        # Create the final response text
        response_text = "\n".join(final_text)
        
        # Append query and response to chat history
        self.chat_history.append({"query": query, "response": response_text})
        
        # Update token count estimation (rough approximation)
        query_chars = len(query)
        response_chars = len(response_text)
        estimated_tokens = int((query_chars + response_chars) * self.token_count_per_char)
        self.approx_token_count += estimated_tokens

        return response_text

    async def get_user_input(self, prompt_text: str = "\nQuery") -> str:
        """Get user input with full keyboard navigation support"""
        try:
            # Use prompt_async instead of prompt
            user_input = await self.prompt_session.prompt_async(
                f"{prompt_text}: ",
                style=self.prompt_style
            )
            return user_input
        except KeyboardInterrupt:
            return "quit"
        except EOFError:
            return "quit"
        
    async def display_check_for_updates(self):
        # Check for updates
        try:
            update_available, current_version, latest_version = await check_for_updates()
            if update_available:
                self.console.print(Panel(
                    f"[bold yellow]New version available![/bold yellow]\n\n"
                    f"Current version: [cyan]{current_version}[/cyan]\n"
                    f"Latest version: [green]{latest_version}[/green]\n\n"
                    f"Upgrade with: [bold white]pip install --upgrade mcp-client-for-ollama[/bold white]",
                    title="Update Available", border_style="yellow", expand=False
                ))
        except Exception as e:
            # Silently fail - version check should not block program usage
            pass

    async def chat_loop(self):
        """Run an interactive chat loop"""
        self.clear_console()        
        self.console.print(Panel(Text.from_markup("[bold green]Welcome to the MCP Client for Ollama[/bold green]", justify="center"), expand=True, border_style="green"))
        self.display_available_tools()
        self.display_current_model()
        self.print_help()
        await self.display_check_for_updates()

        while True:
            try:
                # Use await to call the async method
                query = await self.get_user_input("Query")

                if query.lower() in ['quit', 'q']:
                    self.console.print("[yellow]Exiting...[/yellow]")
                    break
                
                if query.lower() in ['tools', 't']:
                    self.select_tools()
                    continue
                    
                if query.lower() in ['help', 'h']:
                    self.print_help()
                    continue
                
                if query.lower() in ['model', 'm']:
                    await self.select_model()
                    continue
                
                if query.lower() in ['context', 'c']:
                    self.toggle_context_retention()
                    continue
                
                if query.lower() in ['clear', 'cc']:
                    self.clear_context()
                    continue

                if query.lower() in ['context-info', 'ci']:
                    self.display_context_stats()
                    continue
                    
                if query.lower() in ['cls', 'clear-screen']:
                    self.clear_console()
                    self.display_available_tools()
                    self.display_current_model()
                    continue
                    
                if query.lower() in ['save-config', 'sc']:
                    # Ask for config name, defaulting to "default"
                    config_name = await self.get_user_input("Config name (or press Enter for default)")
                    if not config_name or config_name.strip() == "":
                        config_name = "default"
                    self.save_configuration(config_name)
                    continue
                    
                if query.lower() in ['load-config', 'lc']:
                    # Ask for config name, defaulting to "default"
                    config_name = await self.get_user_input("Config name to load (or press Enter for default)")
                    if not config_name or config_name.strip() == "":
                        config_name = "default"
                    self.load_configuration(config_name)
                    # Update display after loading
                    self.display_available_tools()
                    self.display_current_model()
                    continue
                    
                if query.lower() in ['reset-config', 'rc']:
                    self.reset_configuration()
                    # Update display after resetting
                    self.display_available_tools()
                    self.display_current_model()
                    continue

                # Check if query is too short and not a special command
                if len(query.strip()) < 5:
                    self.console.print("[yellow]Query must be at least 5 characters long.[/yellow]")
                    continue

                try:
                    response = await self.process_query(query)
                    if response:
                        self.console.print(Markdown(response))                                                
                    else:
                        self.console.print("[red]No response received.[/red]")
                except ollama.ResponseError as e:
                    # Extract error message without the traceback
                    error_msg = str(e)
                    self.console.print(Panel(f"[bold red]Ollama Error:[/bold red] {error_msg}", 
                                          border_style="red", expand=False))
                    
                    # If it's a "model not found" error, suggest how to fix it
                    if "not found" in error_msg.lower() and "try pulling it first" in error_msg.lower():
                        model_name = self.model                        
                        self.console.print(f"\n[yellow]To download this model, run the following command in a new terminal window:[/yellow]")
                        self.console.print(f"[bold cyan]ollama pull {model_name}[/bold cyan]\n")
                        self.console.print(f"[yellow]Or, you can use a different model by typing[/yellow] [bold cyan]model[/bold cyan] [yellow]or[/yellow] [bold cyan]m[/bold cyan] [yellow]to select from available models[/yellow]\n")                        

            except ollama.ConnectionError as e:
                self.console.print(Panel(f"[bold red]Connection Error:[/bold red] {str(e)}", 
                                      border_style="red", expand=False))
                self.console.print("[yellow]Make sure Ollama is running with 'ollama serve'[/yellow]")
                
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
                self.console.print_exception()
                
    def print_help(self):
        """Print available commands"""
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

    def toggle_context_retention(self):
        """Toggle whether to retain previous conversation context when sending queries"""
        self.retain_context = not self.retain_context
        status = "enabled" if self.retain_context else "disabled"
        self.console.print(f"[green]Context retention {status}![/green]")
        # Display current context stats
        self.display_context_stats()
        
    def clear_context(self):
        """Clear conversation history and token count"""
        original_history_length = len(self.chat_history)
        self.chat_history = []
        self.approx_token_count = 0
        self.console.print(f"[green]Context cleared! Removed {original_history_length} conversation entries.[/green]")
        
    def display_context_stats(self):
        """Display information about the current context window usage"""
        history_count = len(self.chat_history)
        
        self.console.print(Panel(
            f"[bold]Context Statistics[/bold]\n"
            f"Context retention: [{'green' if self.retain_context else 'red'}]{'Enabled' if self.retain_context else 'Disabled'}[/{'green' if self.retain_context else 'red'}]\n"
            f"Conversation entries: {history_count}\n"
            f"Approximate token count: {self.approx_token_count:,}",
            title="Context Window", border_style="cyan", expand=False
        ))

    def save_configuration(self, config_name=None):
        """Save current tool configuration and model settings to a file
        
        Args:
            config_name: Optional name for the config (defaults to 'default')
        """
        # Create config directory if it doesn't exist
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
        
        # Default to 'default' if no config name provided
        if not config_name:
            config_name = "default"
        
        # Sanitize filename
        config_name = ''.join(c for c in config_name if c.isalnum() or c in ['-', '_']).lower()
        if not config_name:
            config_name = "default"
            
        # Create config file path
        if config_name == "default":
            config_path = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
        else:
            config_path = os.path.join(DEFAULT_CONFIG_DIR, f"{config_name}.json")
        
        # Build config data
        config_data = {
            "model": self.model,
            "enabledTools": self.enabled_tools,
            "contextSettings": {
                "retainContext": self.retain_context
            }
        }
        
        # Write to file
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.console.print(Panel(
                f"[green]Configuration saved successfully to:[/green]\n"
                f"[blue]{config_path}[/blue]",
                title="Config Saved", border_style="green", expand=False
            ))
            return True
        except Exception as e:
            self.console.print(Panel(
                f"[red]Error saving configuration:[/red]\n"
                f"{str(e)}",
                title="Error", border_style="red", expand=False
            ))
            return False
    
    def load_configuration(self, config_name=None):
        """Load tool configuration and model settings from a file
        
        Args:
            config_name: Optional name of the config to load (defaults to 'default')
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        # Default to 'default' if no config name provided
        if not config_name:
            config_name = "default"
            
        # Sanitize filename
        config_name = ''.join(c for c in config_name if c.isalnum() or c in ['-', '_']).lower()
        if not config_name:
            config_name = "default"
            
        # Create config file path
        if config_name == "default":
            config_path = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
        else:
            config_path = os.path.join(DEFAULT_CONFIG_DIR, f"{config_name}.json")
            
        # Check if config file exists
        if not os.path.exists(config_path):
            self.console.print(Panel(
                f"[yellow]Configuration file not found:[/yellow]\n"
                f"[blue]{config_path}[/blue]",
                title="Config Not Found", border_style="yellow", expand=False
            ))
            return False
            
        # Read config file
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            # Load model if specified
            if "model" in config_data:
                self.model = config_data["model"]
                
            # Load enabled tools if specified
            if "enabledTools" in config_data:
                loaded_tools = config_data["enabledTools"]
                
                # Only apply tools that actually exist in our available tools
                available_tool_names = {tool.name for tool in self.available_tools}
                for tool_name, enabled in loaded_tools.items():
                    if tool_name in available_tool_names:
                        self.enabled_tools[tool_name] = enabled
                        
            # Load context settings if specified
            if "contextSettings" in config_data:
                if "retainContext" in config_data["contextSettings"]:
                    self.retain_context = config_data["contextSettings"]["retainContext"]                
                    
            self.console.print(Panel(
                f"[green]Configuration loaded successfully from:[/green]\n"
                f"[blue]{config_path}[/blue]",
                title="Config Loaded", border_style="green", expand=False
            ))
            return True
        except Exception as e:
            self.console.print(Panel(
                f"[red]Error loading configuration:[/red]\n"
                f"{str(e)}",
                title="Error", border_style="red", expand=False
            ))
            return False
            
    def reset_configuration(self):
        """Reset tool configuration to default (all tools enabled)"""
        # Enable all tools
        for tool in self.available_tools:
            self.enabled_tools[tool.name] = True
            
        # Reset context settings
        self.retain_context = True
        
        self.console.print(Panel(
            "[green]Configuration reset to defaults![/green]\n"
            "• All tools enabled\n"
            "• Context retention enabled\n"
            "• Context info display disabled",
            title="Config Reset", border_style="green", expand=False
        ))
        return True

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def check_for_updates():
    """Check if a newer version of the package is available on PyPI.
    
    Returns:
        Tuple[bool, str, str]: (update_available, current_version, latest_version)
    """
    from mcp_client_for_ollama import __version__ as current_version
    
    try:
        # Request package info from PyPI
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pypi.org/pypi/mcp-client-for-ollama/json") as response:
                if response.status != 200:
                    return False, current_version, current_version
                
                data = await response.json()
                latest_version = data.get("info", {}).get("version", current_version)
                
                # Compare versions (treating them as tuples of integers)
                def parse_version(version_str):
                    # Extract numbers from version string (handles formats like 0.1.11)
                    return tuple(map(int, re.findall(r'\d+', version_str)))
                
                current_parsed = parse_version(current_version)
                latest_parsed = parse_version(latest_version)
                
                update_available = latest_parsed > current_parsed
                return update_available, current_version, latest_version
    
    except Exception:
        # Return no update available on error
        return False, current_version, current_version


async def main():
    parser = argparse.ArgumentParser(description="MCP Client for Ollama")
    
    # Server configuration options
    server_group = parser.add_argument_group("server options")
    server_group.add_argument("--mcp-server", help="Path to a server script (.py or .js)", action="append")
    server_group.add_argument("--servers-json", help="Path to a JSON file with server configurations")
    server_group.add_argument("--auto-discovery", action="store_true", default=False,
                            help=f"Auto-discover servers from Claude's config at {DEFAULT_CLAUDE_CONFIG} - Default option")
    # Model options
    model_group = parser.add_argument_group("model options")
    model_group.add_argument("--model", default="qwen2.5:7b", help="Ollama model to use. Default: 'qwen2.5:7b'")
    
    # Add version flag
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
     # Add a function to modify args after parsing
    def parse_args_with_defaults():
        args = parser.parse_args()
        # If none of the server arguments are provided, enable auto-discovery
        if not (args.mcp_server or args.servers_json or args.auto_discovery):
            args.auto_discovery = True
        return args
    
    args = parse_args_with_defaults()

    console = Console()

    # Create a temporary client to check if Ollama is running
    client = MCPClient(model=args.model)
    if not await client.check_ollama_running():
        console.print(Panel(
            "[bold red]Error: Ollama is not running![/bold red]\n\n"
            "This client requires Ollama to be running to process queries.\n"
            "Please start Ollama by running the 'ollama serve' command in a terminal.",
            title="Ollama Not Running", border_style="red", expand=False
        ))
        return

    # Determine which server config to use
    config_path = None
    if args.auto_discovery:
        if os.path.exists(DEFAULT_CLAUDE_CONFIG):
            config_path = DEFAULT_CLAUDE_CONFIG
        else:
            console.print(f"[yellow]Warning: Claude config not found at {DEFAULT_CLAUDE_CONFIG}[/yellow]")
    elif args.servers_json:
        if os.path.exists(args.servers_json):
            config_path = args.servers_json
        else:
            console.print(f"[bold red]Error: Specified JSON config file not found: {args.servers_json}[/bold red]")
            return

    # Validate that we have at least one server source
    if not args.mcp_server and not config_path:
        parser.error("At least one of --mcp-server, --servers-json, or --auto-discovery must be provided")

    # Validate mcp-server paths exist
    if args.mcp_server:
        for server_path in args.mcp_server:
            if not os.path.exists(server_path):
                console.print(f"[bold red]Error: Server script not found: {server_path}[/bold red]")
                return
    try:
        await client.connect_to_servers(args.mcp_server, config_path)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
