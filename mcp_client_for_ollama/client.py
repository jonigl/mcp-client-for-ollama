import argparse
import asyncio
import json
import os
import shutil
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
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
import ollama
from ollama import ChatResponse

from . import __version__
from .config.manager import ConfigManager 
from .utils.version import check_for_updates
from .utils.constants import DEFAULT_CLAUDE_CONFIG, DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE, TOKEN_COUNT_PER_CHAR, DEFAULT_MODEL
from .server.connector import ServerConnector
from .models.manager import ModelManager

class MCPClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        # Initialize session and client objects
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient()
        self.console = Console()
        self.config_manager = ConfigManager(self.console)
        # Initialize the server connector
        self.server_connector = ServerConnector(self.exit_stack, self.console)
        # Initialize the model manager
        self.model_manager = ModelManager(console=self.console, default_model=model)
        # Store server and tool data
        self.sessions = {}  # Dict to store multiple sessions
        self.available_tools: List[Tool] = []
        self.enabled_tools: Dict[str, bool] = {}
        # UI components
        self.chat_history = []  # Add chat history list to store interactions
        self.prompt_session = PromptSession()
        self.prompt_style = Style.from_dict({
            'prompt': 'ansibrightyellow bold',
        })
        # Context retention settings
        self.retain_context = True  # By default, retain conversation context        
        self.approx_token_count = 0  # Approximate token count for the conversation
        self.token_count_per_char = TOKEN_COUNT_PER_CHAR  # Rough approximation of tokens per character
        
    async def check_ollama_running(self) -> bool:
        """Check if Ollama is running by making a request to its API
        
        Returns:
            bool: True if Ollama is running, False otherwise
        """
        return await self.model_manager.check_ollama_running()

    def display_current_model(self):
        """Display the currently selected model"""
        self.model_manager.display_current_model()
                               
    async def select_model(self):
        """Let the user select an Ollama model from the available ones"""
        await self.model_manager.select_model_interactive(clear_console_func=self.clear_console)
        
        # After model selection, redisplay context
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

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
    
    async def connect_to_servers(self, server_paths=None, config_path=None, auto_discovery=False):
        """Connect to one or more MCP servers using the ServerConnector
        
        Args:
            server_paths: List of paths to server scripts (.py or .js)
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers
        """
        # Connect to servers using the server connector
        sessions, available_tools, enabled_tools = await self.server_connector.connect_to_servers(
            server_paths=server_paths,
            config_path=config_path,
            auto_discovery=auto_discovery
        )
        
        # Store the results
        self.sessions = sessions
        self.available_tools = available_tools
        self.enabled_tools = enabled_tools

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
                # Use the server connector to enable all tools
                self.server_connector.enable_all_tools()
                # Update our local copy
                self.enabled_tools = self.server_connector.get_enabled_tools()
                self.clear_console()
                result_message = "[green]All tools enabled![/green]"                
                continue
            
            if selection in ['n', 'none']:
                # Use the server connector to disable all tools
                self.server_connector.disable_all_tools()
                # Update our local copy
                self.enabled_tools = self.server_connector.get_enabled_tools()
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
                        # Also update in the server connector
                        self.server_connector.set_tool_status(tool.name, new_state)
                    
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
                        new_state = not self.enabled_tools[tool.name]
                        self.enabled_tools[tool.name] = new_state
                        # Also update in the server connector
                        self.server_connector.set_tool_status(tool.name, new_state)
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

        # Get current model from the model manager
        model = self.model_manager.get_current_model()

        # Initial Ollama API call
        with self.console.status("[cyan]Thinking...[/cyan]"):
            response: ChatResponse = await self.ollama.chat(
                model=model,
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
                        model=model,
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
                        model_name = self.model_manager.get_current_model()                       
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
        # Build config data
        config_data = {
            "model": self.model_manager.get_current_model(),
            "enabledTools": self.enabled_tools,
            "contextSettings": {
                "retainContext": self.retain_context
            }
        }
        
        # Use the ConfigManager to save the configuration
        return self.config_manager.save_configuration(config_data, config_name)
    
    def load_configuration(self, config_name=None):
        """Load tool configuration and model settings from a file
        
        Args:
            config_name: Optional name of the config to load (defaults to 'default')
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        # Use the ConfigManager to load the configuration
        config_data = self.config_manager.load_configuration(config_name)
        
        if not config_data:
            return False
            
        # Apply the loaded configuration
        if "model" in config_data:
            self.model_manager.set_model(config_data["model"])
            
        # Load enabled tools if specified
        if "enabledTools" in config_data:
            loaded_tools = config_data["enabledTools"]
            
            # Only apply tools that actually exist in our available tools
            available_tool_names = {tool.name for tool in self.available_tools}
            for tool_name, enabled in loaded_tools.items():
                if tool_name in available_tool_names:
                    self.enabled_tools[tool_name] = enabled
                    # Also update in the server connector
                    self.server_connector.set_tool_status(tool_name, enabled)
                    
        # Load context settings if specified
        if "contextSettings" in config_data and "retainContext" in config_data["contextSettings"]:
            self.retain_context = config_data["contextSettings"]["retainContext"]
        
        return True
        
    def reset_configuration(self):
        """Reset tool configuration to default (all tools enabled)"""
        # Use the ConfigManager to get the default configuration
        config_data = self.config_manager.reset_configuration()
        
        # Enable all tools in the server connector
        self.server_connector.enable_all_tools()
        # Update our local copy
        self.enabled_tools = self.server_connector.get_enabled_tools()
            
        # Reset context settings from the default configuration
        if "contextSettings" in config_data and "retainContext" in config_data["contextSettings"]:
            self.retain_context = config_data["contextSettings"]["retainContext"]
        
        return True

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


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
    model_group.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to use. Default: '{DEFAULT_MODEL}'")
    
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

    # Handle server configuration options - only use one source to prevent duplicates
    config_path = None
    auto_discovery = False
    
    if args.servers_json:
        # If --servers-json is provided, use that and disable auto-discovery
        if os.path.exists(args.servers_json):
            config_path = args.servers_json
        else:
            console.print(f"[bold red]Error: Specified JSON config file not found: {args.servers_json}[/bold red]")
            return
    elif args.auto_discovery:
        # If --auto-discovery is provided, use that and set config_path to None
        auto_discovery = True
        if os.path.exists(DEFAULT_CLAUDE_CONFIG):
            console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
        else:
            console.print(f"[yellow]Warning: Claude config not found at {DEFAULT_CLAUDE_CONFIG}[/yellow]")
    else:
        # If neither is provided, check if DEFAULT_CLAUDE_CONFIG exists and use auto_discovery
        if not args.mcp_server:
            if os.path.exists(DEFAULT_CLAUDE_CONFIG):
                console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
                auto_discovery = True
            else:
                console.print(f"[yellow]Warning: No servers specified and Claude config not found.[/yellow]")

    # Validate that we have at least one server source
    if not args.mcp_server and not config_path and not auto_discovery:
        parser.error("At least one of --mcp-server, --servers-json, or --auto-discovery must be provided")

    # Validate mcp-server paths exist
    if args.mcp_server:
        for server_path in args.mcp_server:
            if not os.path.exists(server_path):
                console.print(f"[bold red]Error: Server script not found: {server_path}[/bold red]")
                return
    try:
        await client.connect_to_servers(args.mcp_server, config_path, auto_discovery)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
