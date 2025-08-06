"""MCP Client for Ollama - A TUI client for interacting with Ollama models and MCP servers"""
import asyncio
import os
from contextlib import AsyncExitStack
from typing import List, Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import ollama

from . import __version__
from .config.manager import ConfigManager
from .utils.version import check_for_updates
from .utils.constants import DEFAULT_CLAUDE_CONFIG, DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_COMPLETION_STYLE
from .server.connector import ServerConnector
from .models.manager import ModelManager
from .models.config_manager import ModelConfigManager
from .tools.manager import ToolManager
from .utils.streaming import StreamingManager
from .utils.tool_display import ToolDisplayManager
from .utils.hil_manager import HumanInTheLoopManager
from .utils.fzf_style_completion import FZFStyleCompleter


class MCPClient:
    """Main client class for interacting with Ollama and MCP servers"""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_OLLAMA_HOST):
        # Initialize session and client objects
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient(host=host)
        self.console = Console()
        self.config_manager = ConfigManager(self.console)
        # Initialize the server connector
        self.server_connector = ServerConnector(self.exit_stack, self.console)
        # Initialize the model manager
        self.model_manager = ModelManager(console=self.console, default_model=model, ollama=self.ollama)
        # Initialize the model config manager
        self.model_config_manager = ModelConfigManager(console=self.console)
        # Initialize the tool manager with server connector reference
        self.tool_manager = ToolManager(console=self.console, server_connector=self.server_connector)
        # Initialize the streaming manager
        self.streaming_manager = StreamingManager(console=self.console)
        # Initialize the tool display manager
        self.tool_display_manager = ToolDisplayManager(console=self.console)
        # Initialize the HIL manager
        self.hil_manager = HumanInTheLoopManager(console=self.console)
        # Store server and tool data
        self.sessions = {}  # Dict to store multiple sessions
        # UI components
        self.chat_history = []  # Add chat history list to store interactions
        # Command completer for interactive prompts
        self.prompt_session = PromptSession(
            completer=FZFStyleCompleter(),
            style=Style.from_dict(DEFAULT_COMPLETION_STYLE)
        )
        # Context retention settings
        self.retain_context = True  # By default, retain conversation context
        self.actual_token_count = 0  # Actual token count from Ollama metrics
        # Thinking mode settings
        self.thinking_mode = True  # By default, thinking mode is enabled for models that support it
        self.show_thinking = False   # By default, thinking text is hidden after completion
        # Tool display settings
        self.show_tool_execution = True  # By default, show tool execution displays
        # Metrics display settings
        self.show_metrics = False  # By default, don't show metrics after each query
        self.default_configuration_status = False  # Track if default configuration was loaded successfully

        # Store server connection parameters for reloading
        self.server_connection_params = {
            'server_paths': None,
            'config_path': None,
            'auto_discovery': False
        }

    def display_current_model(self):
        """Display the currently selected model"""
        self.model_manager.display_current_model()

    async def supports_thinking_mode(self) -> bool:
        """Check if the current model supports thinking mode by checking its capabilities

        Returns:
            bool: True if the current model supports thinking mode, False otherwise
        """
        try:
            current_model = self.model_manager.get_current_model()
            # Query the model's capabilities using ollama.show()
            model_info = await self.ollama.show(current_model)

            # Check if the model has 'thinking' capability
            if 'capabilities' in model_info and model_info['capabilities']:
                return 'thinking' in model_info['capabilities']

            return False
        except Exception:
            # If we can't determine capabilities, assume no thinking support
            return False

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
        self.tool_manager.display_available_tools()

    async def connect_to_servers(self, server_paths=None, server_urls=None, config_path=None, auto_discovery=False):
        """Connect to one or more MCP servers using the ServerConnector

        Args:
            server_paths: List of paths to server scripts (.py or .js)
            server_urls: List of URLs for SSE or Streamable HTTP servers
            config_path: Path to JSON config file with server configurations
            auto_discovery: Whether to automatically discover servers
        """
        # Store connection parameters for potential reload
        self.server_connection_params = {
            'server_paths': server_paths,
            'server_urls': server_urls,
            'config_path': config_path,
            'auto_discovery': auto_discovery
        }

        # Connect to servers using the server connector
        sessions, available_tools, enabled_tools = await self.server_connector.connect_to_servers(
            server_paths=server_paths,
            server_urls=server_urls,
            config_path=config_path,
            auto_discovery=auto_discovery
        )

        # Store the results
        self.sessions = sessions

        # Set up the tool manager with the available tools and their enabled status
        self.tool_manager.set_available_tools(available_tools)
        self.tool_manager.set_enabled_tools(enabled_tools)

    def select_tools(self):
        """Let the user select which tools to enable using interactive prompts with server-based grouping"""
        # Call the tool manager's select_tools method
        self.tool_manager.select_tools(clear_console_func=self.clear_console)

        # Display the chat history and current state after selection
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

    def configure_model_options(self):
        """Let the user configure model parameters like system prompt, temperature, etc."""
        self.model_config_manager.configure_model_interactive(clear_console_func=self.clear_console)

        # Display the chat history and current state after selection
        self.display_available_tools()
        self.display_current_model()
        self._display_chat_history()

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
                self.console.print("[bold blue]Answer:[/bold blue]")
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

        # Add system prompt if one is configured
        system_prompt = self.model_config_manager.get_system_prompt()
        if system_prompt:
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

        # Get enabled tools from the tool manager
        enabled_tool_objects = self.tool_manager.get_enabled_tool_objects()

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

        # Get model options in Ollama format
        model_options = self.model_config_manager.get_ollama_options()

        # Prepare chat parameters
        chat_params = {
            "model": model,
            "messages": messages,
            "stream": True,
            "tools": available_tools,
            "options": model_options
        }

        # Add thinking parameter if thinking mode is enabled and model supports it
        if await self.supports_thinking_mode():
            chat_params["think"] = self.thinking_mode

        # Initial Ollama API call with the query and available tools
        stream = await self.ollama.chat(**chat_params)

        # Process the streaming response with thinking mode support
        response_text = ""
        tool_calls = []
        response_text, tool_calls, metrics = await self.streaming_manager.process_streaming_response(
            stream,
            thinking_mode=self.thinking_mode,
            show_thinking=self.show_thinking,
            show_metrics=self.show_metrics
        )

        # Update actual token count from metrics if available
        if metrics and metrics.get('eval_count'):
            self.actual_token_count += metrics['eval_count']
        # Check if there are any tool calls in the response
        if len(tool_calls) > 0 and self.tool_manager.get_enabled_tool_objects():
            for tool in tool_calls:
                tool_name = tool.function.name
                tool_args = tool.function.arguments

                # Parse server name and actual tool name from the qualified name
                server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)

                if not server_name or server_name not in self.sessions:
                    self.console.print(f"[red]Error: Unknown server for tool {tool_name}[/red]")
                    continue

                # Execute tool call
                self.tool_display_manager.display_tool_execution(tool_name, tool_args, show=self.show_tool_execution)

                # Request HIL confirmation if enabled
                should_execute = await self.hil_manager.request_tool_confirmation(
                    tool_name, tool_args
                )

                if not should_execute:
                    tool_response = "Tool call was skipped by user"
                    self.tool_display_manager.display_tool_response(tool_name, tool_args, tool_response, show=self.show_tool_execution)
                    messages.append({
                        "role": "tool",
                        "content": tool_response,
                        "name": tool_name
                    })
                    continue

                # Call the tool on the specified server
                result = None
                with self.console.status(f"[cyan]⏳ Running {tool_name}...[/cyan]"):
                    result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)

                tool_response = f"{result.content[0].text}"

                # Display the tool response
                self.tool_display_manager.display_tool_response(tool_name, tool_args, tool_response, show=self.show_tool_execution)

                messages.append({
                    "role": "tool",
                    "content": tool_response,
                    "name": tool_name
                })

            # Get stream response from Ollama with the tool results
            chat_params_followup = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": model_options
            }

            # Add thinking parameter if thinking mode is enabled and model supports it
            if await self.supports_thinking_mode():
                chat_params_followup["think"] = self.thinking_mode

            stream = await self.ollama.chat(**chat_params_followup)

            # Process the streaming response with thinking mode support
            response_text, _, followup_metrics = await self.streaming_manager.process_streaming_response(
                stream,
                thinking_mode=self.thinking_mode,
                show_thinking=self.show_thinking,
                show_metrics=self.show_metrics
            )

            # Update actual token count from followup metrics if available
            if followup_metrics and followup_metrics.get('eval_count'):
                self.actual_token_count += followup_metrics['eval_count']

        if not response_text:
            self.console.print("[red]No content response received.[/red]")
            response_text = ""

        # Append query and response to chat history
        self.chat_history.append({"query": query, "response": response_text})

        return response_text

    async def get_user_input(self, prompt_text: str = None) -> str:
        """Get user input with full keyboard navigation support"""
        try:
            if prompt_text is None:
                model_name = self.model_manager.get_current_model().split(':')[0]
                tool_count = len(self.tool_manager.get_enabled_tool_objects())

                # Simple and readable
                prompt_text = f"{model_name}"

                # Add thinking indicator
                if self.thinking_mode and await self.supports_thinking_mode():
                    prompt_text += "/show-thinking" if self.show_thinking else "/thinking"

                # Add tool count
                if tool_count > 0:
                    prompt_text += f"/{tool_count}-tool" if tool_count == 1 else f"/{tool_count}-tools"

            user_input = await self.prompt_session.prompt_async(
                f"{prompt_text}❯ "
            )
            return user_input
        except KeyboardInterrupt:
            return "quit"
        except EOFError:
            return "quit"

    async def display_check_for_updates(self):
        # Check for updates
        try:
            update_available, current_version, latest_version = check_for_updates()
            if update_available:
                self.console.print(Panel(
                    f"[bold yellow]New version available![/bold yellow]\n\n"
                    f"Current version: [cyan]{current_version}[/cyan]\n"
                    f"Latest version: [green]{latest_version}[/green]\n\n"
                    f"Upgrade with: [bold white]pip install --upgrade mcp-client-for-ollama[/bold white]",
                    title="Update Available", border_style="yellow", expand=False
                ))
        except Exception:
            # Silently fail - version check should not block program usage
            pass

    async def chat_loop(self):
        """Run an interactive chat loop"""
        self.clear_console()
        self.console.print(Panel(Text.from_markup("[bold green]Welcome to the MCP Client for Ollama 🦙[/bold green]", justify="center"), expand=True, border_style="green"))
        self.display_available_tools()
        self.display_current_model()
        self.print_help()
        self.print_auto_load_default_config_status()
        await self.display_check_for_updates()

        while True:
            try:
                # Use await to call the async method
                query = await self.get_user_input()

                if query.lower() in ['quit', 'q', 'exit']:
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

                if query.lower() in ['model-config', 'mc']:
                    self.configure_model_options()
                    continue

                if query.lower() in ['context', 'c']:
                    self.toggle_context_retention()
                    continue

                if query.lower() in ['thinking-mode', 'tm']:
                    await self.toggle_thinking_mode()
                    continue

                if query.lower() in ['show-thinking', 'st']:
                    await self.toggle_show_thinking()
                    continue

                if query.lower() in ['show-tool-execution', 'ste']:
                    self.toggle_show_tool_execution()
                    continue

                if query.lower() in ['show-metrics', 'sm']:
                    self.toggle_show_metrics()
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

                if query.lower() in ['reload-servers', 'rs']:
                    await self.reload_servers()
                    continue

                if query.lower() in ['human-in-the-loop', 'hil']:
                    self.hil_manager.toggle()
                    continue

                # Check if query is too short and not a special command
                if len(query.strip()) < 5:
                    self.console.print("[yellow]Query must be at least 5 characters long.[/yellow]")
                    continue

                try:
                    await self.process_query(query)
                except ollama.ResponseError as e:
                    # Extract error message without the traceback
                    error_msg = str(e)
                    if "does not support tools" in error_msg.lower():
                        model_name = self.model_manager.get_current_model()
                        self.console.print(Panel(
                            f"[bold red]Model Error:[/bold red] The model [bold blue]{model_name}[/bold blue] does not support tools.\n\n"
                            "To use tools, switch to a model that supports them by typing [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan]\n\n"
                            "You can still use this model without tools by [bold]disabling all tools[/bold] with [bold cyan]tools[/bold cyan] or [bold cyan]t[/bold cyan]",
                            title="Tools Not Supported",
                            border_style="red", expand=False
                        ))
                    else:
                        self.console.print(Panel(f"[bold red]Ollama Error:[/bold red] {error_msg}",
                                                 border_style="red", expand=False))

                    # If it's a "model not found" error, suggest how to fix it
                    if "not found" in error_msg.lower() and "try pulling it first" in error_msg.lower():
                        model_name = self.model_manager.get_current_model()
                        self.console.print(Panel(
                            "[bold yellow]Model Not Found[/bold yellow]\n\n"
                            "To download this model, run the following command in a new terminal window:\n"
                            f"[bold cyan]ollama pull {model_name}[/bold cyan]\n\n"
                            "Or, you can use a different model by typing [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan] to select from available models",
                            title="Model Not Available",
                            border_style="yellow", expand=False
                        ))

            except Exception as e:
                self.console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", title="Exception", border_style="red", expand=False))
                self.console.print_exception()

    def print_help(self):
        """Print available commands"""
        self.console.print(Panel(
            "[bold yellow]Available Commands:[/bold yellow]\n\n"

            "[bold cyan]Model:[/bold cyan]\n"
            "• Type [bold]model[/bold] or [bold]m[/bold] to select a model\n"
            "• Type [bold]model-config[/bold] or [bold]mc[/bold] to configure system prompt and model parameters\n"
            f"• Type [bold]thinking-mode[/bold] or [bold]tm[/bold] to toggle thinking mode\n"
            "• Type [bold]show-thinking[/bold] or [bold]st[/bold] to toggle thinking text visibility\n"
            "• Type [bold]show-metrics[/bold] or [bold]sm[/bold] to toggle performance metrics display\n\n"

            "[bold cyan]MCP Servers and Tools:[/bold cyan]\n"
            "• Type [bold]tools[/bold] or [bold]t[/bold] to configure tools\n"
            "• Type [bold]show-tool-execution[/bold] or [bold]ste[/bold] to toggle tool execution display\n"
            "• Type [bold]human-in-the-loop[/bold] or [bold]hil[/bold] to toggle Human-in-the-Loop confirmations\n"
            "• Type [bold]reload-servers[/bold] or [bold]rs[/bold] to reload MCP servers\n\n"

            "[bold cyan]Context:[/bold cyan]\n"
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
            "• Type [bold]quit[/bold], [bold]q[/bold], [bold]exit[/bold], or [bold]Ctrl+D[/bold] to exit the client\n",
            title="[bold]Help[/bold]", border_style="yellow", expand=False))

    def toggle_context_retention(self):
        """Toggle whether to retain previous conversation context when sending queries"""
        self.retain_context = not self.retain_context
        status = "enabled" if self.retain_context else "disabled"
        self.console.print(f"[green]Context retention {status}![/green]")
        # Display current context stats
        self.display_context_stats()

    async def toggle_thinking_mode(self):
        """Toggle thinking mode on/off (only for supported models)"""
        if not await self.supports_thinking_mode():
            current_model = self.model_manager.get_current_model()
            model_base_name = current_model.split(":")[0]
            self.console.print(Panel(
                f"[bold red]Thinking mode is not supported for model '{model_base_name}'[/bold red]\n\n"
                f"Thinking mode is only available for models that have the 'thinking' capability.\n"
                f"\nCurrent model: [yellow]{current_model}[/yellow]\n"
                f"Use [bold cyan]model[/bold cyan] or [bold cyan]m[/bold cyan] to switch to a supported model.",
                title="Thinking Mode Not Available", border_style="red", expand=False
            ))
            return

        self.thinking_mode = not self.thinking_mode
        status = "enabled" if self.thinking_mode else "disabled"
        self.console.print(f"[green]Thinking mode {status}![/green]")

        if self.thinking_mode:
            self.console.print("[cyan]🤔 The model will now show its reasoning process.[/cyan]")
        else:
            self.console.print("[cyan]The model will now provide direct responses.[/cyan]")

    async def toggle_show_thinking(self):
        """Toggle whether thinking text remains visible after completion"""
        if not self.thinking_mode:
            self.console.print(Panel(
                f"[bold yellow]Thinking mode is currently disabled[/bold yellow]\n\n"
                f"Enable thinking mode first using [bold cyan]thinking[/bold cyan] or [bold cyan]th[/bold cyan] command.\n"
                f"This setting only applies when thinking mode is active.",
                title="Show Thinking Setting", border_style="yellow", expand=False
            ))
            return

        if not await self.supports_thinking_mode():
            current_model = self.model_manager.get_current_model()
            model_base_name = current_model.split(":")[0]
            self.console.print(Panel(
                f"[bold red]Thinking mode is not supported for model '{model_base_name}'[/bold red]\n\n"
                f"This setting only applies to models that have the 'thinking' capability.",
                title="Show Thinking Not Available", border_style="red", expand=False
            ))
            return

        self.show_thinking = not self.show_thinking
        status = "visible" if self.show_thinking else "hidden"
        self.console.print(f"[green]Thinking text will be {status} after completion![/green]")

        if self.show_thinking:
            self.console.print("[cyan]💭 The reasoning process will remain visible in the final response.[/cyan]")
        else:
            self.console.print("[cyan]🧹 The reasoning process will be hidden, showing only the final answer.[/cyan]")

    def toggle_show_tool_execution(self):
        """Toggle whether tool execution displays are shown"""
        self.show_tool_execution = not self.show_tool_execution
        status = "visible" if self.show_tool_execution else "hidden"
        self.console.print(f"[green]Tool execution displays will be {status}![/green]")

        if self.show_tool_execution:
            self.console.print("[cyan]🔧 Tool execution details will be displayed when tools are called.[/cyan]")
        else:
            self.console.print("[cyan]🔇 Tool execution details will be hidden for a cleaner output.[/cyan]")

    def toggle_show_metrics(self):
        """Toggle whether performance metrics are shown after each query"""
        self.show_metrics = not self.show_metrics
        status = "enabled" if self.show_metrics else "disabled"
        self.console.print(f"[green]Performance metrics display {status}![/green]")

        if self.show_metrics:
            self.console.print("[cyan]📊 Performance metrics will be displayed after each query.[/cyan]")
        else:
            self.console.print("[cyan]🔇 Performance metrics will be hidden for a cleaner output.[/cyan]")

    def clear_context(self):
        """Clear conversation history and token count"""
        original_history_length = len(self.chat_history)
        self.chat_history = []
        self.actual_token_count = 0
        self.console.print(f"[green]Context cleared! Removed {original_history_length} conversation entries.[/green]")

    def display_context_stats(self):
        """Display information about the current context window usage"""
        history_count = len(self.chat_history)

        # For thinking status, show a simplified message. The user can check model capabilities by trying to enable thinking mode
        thinking_status = ""
        if self.thinking_mode:
            thinking_status = f"Thinking mode: [green]Enabled[/green]\n"
            thinking_status += f"Show thinking text: [{'green' if self.show_thinking else 'red'}]{'Visible' if self.show_thinking else 'Hidden'}[/{'green' if self.show_thinking else 'red'}]\n"
        else:
            thinking_status = f"Thinking mode: [red]Disabled[/red]\n"

        self.console.print(Panel(
            f"Context retention: [{'green' if self.retain_context else 'red'}]{'Enabled' if self.retain_context else 'Disabled'}[/{'green' if self.retain_context else 'red'}]\n"
            f"{thinking_status}"
            f"Tool execution display: [{'green' if self.show_tool_execution else 'red'}]{'Enabled' if self.show_tool_execution else 'Disabled'}[/{'green' if self.show_tool_execution else 'red'}]\n"
            f"Performance metrics: [{'green' if self.show_metrics else 'red'}]{'Enabled' if self.show_metrics else 'Disabled'}[/{'green' if self.show_metrics else 'red'}]\n"
            f"Human-in-the-Loop confirmations: [{'green' if self.hil_manager.is_enabled() else 'red'}]{'Enabled' if self.hil_manager.is_enabled() else 'Disabled'}[/{'green' if self.hil_manager.is_enabled() else 'red'}]\n"
            f"Conversation entries: {history_count}\n"
            f"Total tokens generated: {self.actual_token_count:,}",
            title="Context Info", border_style="cyan", expand=False
        ))

    def auto_load_default_config(self):
        """Automatically load the default configuration if it exists."""
        if self.config_manager.config_exists("default"):
            # self.console.print("[cyan]Default configuration found, loading...[/cyan]")
            self.default_configuration_status = self.load_configuration("default")

    def print_auto_load_default_config_status(self):
        """Print the status of the auto-load default configuration."""
        if self.default_configuration_status:
            self.console.print("[green] ✓ Default configuration loaded successfully![/green]")
            self.console.print()

    def save_configuration(self, config_name=None):
        """Save current tool configuration and model settings to a file

        Args:
            config_name: Optional name for the config (defaults to 'default')
        """
        # Build config data
        config_data = {
            "model": self.model_manager.get_current_model(),
            "enabledTools": self.tool_manager.get_enabled_tools(),
            "contextSettings": {
                "retainContext": self.retain_context
            },
            "modelSettings": {
                "thinkingMode": self.thinking_mode,
                "showThinking": self.show_thinking
            },
            "modelConfig": self.model_config_manager.get_config(),
            "displaySettings": {
                "showToolExecution": self.show_tool_execution,
                "showMetrics": self.show_metrics
            },
            "hilSettings": {
                "enabled": self.hil_manager.is_enabled()
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
            available_tool_names = {tool.name for tool in self.tool_manager.get_available_tools()}
            for tool_name, enabled in loaded_tools.items():
                if tool_name in available_tool_names:
                    # Update in the tool manager
                    self.tool_manager.set_tool_status(tool_name, enabled)
                    # Also update in the server connector
                    self.server_connector.set_tool_status(tool_name, enabled)

        # Load context settings if specified
        if "contextSettings" in config_data:
            if "retainContext" in config_data["contextSettings"]:
                self.retain_context = config_data["contextSettings"]["retainContext"]

        # Load model settings if specified
        if "modelSettings" in config_data:
            if "thinkingMode" in config_data["modelSettings"]:
                self.thinking_mode = config_data["modelSettings"]["thinkingMode"]
            if "showThinking" in config_data["modelSettings"]:
                self.show_thinking = config_data["modelSettings"]["showThinking"]

        # Load model configuration if specified
        if "modelConfig" in config_data:
            self.model_config_manager.set_config(config_data["modelConfig"])

        # Load display settings if specified
        if "displaySettings" in config_data:
            if "showToolExecution" in config_data["displaySettings"]:
                self.show_tool_execution = config_data["displaySettings"]["showToolExecution"]
            if "showMetrics" in config_data["displaySettings"]:
                self.show_metrics = config_data["displaySettings"]["showMetrics"]

        # Load HIL settings if specified
        if "hilSettings" in config_data:
            if "enabled" in config_data["hilSettings"]:
                self.hil_manager.set_enabled(config_data["hilSettings"]["enabled"])

        return True

    def reset_configuration(self):
        """Reset tool configuration to default (all tools enabled)"""
        # Use the ConfigManager to get the default configuration
        config_data = self.config_manager.reset_configuration()

        # Enable all tools in the tool manager
        self.tool_manager.enable_all_tools()
        # Enable all tools in the server connector
        self.server_connector.enable_all_tools()

        # Reset context settings from the default configuration
        if "contextSettings" in config_data:
            if "retainContext" in config_data["contextSettings"]:
                self.retain_context = config_data["contextSettings"]["retainContext"]

        # Reset model settings from the default configuration
        if "modelSettings" in config_data:
            if "thinkingMode" in config_data["modelSettings"]:
                self.thinking_mode = config_data["modelSettings"]["thinkingMode"]
            else:
                # Default thinking mode to False if not specified
                self.thinking_mode = False
            if "showThinking" in config_data["modelSettings"]:
                self.show_thinking = config_data["modelSettings"]["showThinking"]
            else:
                # Default show thinking to True if not specified
                self.show_thinking = True

        # Reset display settings from the default configuration
        if "displaySettings" in config_data:
            if "showToolExecution" in config_data["displaySettings"]:
                self.show_tool_execution = config_data["displaySettings"]["showToolExecution"]
            else:
                # Default show tool execution to True if not specified
                self.show_tool_execution = True
            if "showMetrics" in config_data["displaySettings"]:
                self.show_metrics = config_data["displaySettings"]["showMetrics"]
            else:
                # Default show metrics to False if not specified
                self.show_metrics = False

        # Reset HIL settings from the default configuration
        if "hilSettings" in config_data:
            if "enabled" in config_data["hilSettings"]:
                self.hil_manager.set_enabled(config_data["hilSettings"]["enabled"])
            else:
                # Default HIL to True if not specified
                self.hil_manager.set_enabled(True)

        return True

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    async def reload_servers(self):
        """Reload all MCP servers with the same connection parameters"""
        if not any(self.server_connection_params.values()):
            self.console.print("[yellow]No server connection parameters stored. Cannot reload.[/yellow]")
            return

        self.console.print("[cyan]🔄 Reloading MCP servers...[/cyan]")

        try:
            # Store current tool enabled states
            current_enabled_tools = self.tool_manager.get_enabled_tools().copy()

            # Disconnect from all current servers
            await self.server_connector.disconnect_all_servers()

            # Update our exit_stack reference to the new one created by ServerConnector
            self.exit_stack = self.server_connector.exit_stack

            # Reconnect using stored parameters
            await self.connect_to_servers(
                server_paths=self.server_connection_params['server_paths'],
                server_urls=self.server_connection_params['server_urls'],
                config_path=self.server_connection_params['config_path'],
                auto_discovery=self.server_connection_params['auto_discovery']
            )

            # Restore enabled tool states for tools that still exist
            available_tool_names = {tool.name for tool in self.tool_manager.get_available_tools()}
            for tool_name, enabled in current_enabled_tools.items():
                if tool_name in available_tool_names:
                    self.tool_manager.set_tool_status(tool_name, enabled)
                    self.server_connector.set_tool_status(tool_name, enabled)

            self.console.print("[green]✅ MCP servers reloaded successfully![/green]")

            # Display updated status
            self.display_available_tools()

        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error reloading servers:[/bold red] {str(e)}\n\n"
                "You may need to restart the application if servers are not working properly.",
                title="Reload Failed", border_style="red", expand=False
            ))

app = typer.Typer(help="MCP Client for Ollama", context_settings={"help_option_names": ["-h", "--help"]})

@app.command()
def main(
    # MCP Server Configuration
    mcp_server: Optional[List[str]] = typer.Option(
        None, "--mcp-server", "-s",
        help="Path to a server script (.py or .js)",
        rich_help_panel="MCP Server Configuration"
    ),
    mcp_server_url: Optional[List[str]] = typer.Option(
        None, "--mcp-server-url", "-u",
        help="URL for SSE or Streamable HTTP MCP server (e.g., http://localhost:8000/sse, https://domain-name.com/mcp, etc)",
        rich_help_panel="MCP Server Configuration"
    ),
    servers_json: Optional[str] = typer.Option(
        None, "--servers-json", "-j",
        help="Path to a JSON file with server configurations",
        rich_help_panel="MCP Server Configuration"
    ),
    auto_discovery: bool = typer.Option(
        False, "--auto-discovery", "-a",
        help=f"Auto-discover servers from Claude's config at {DEFAULT_CLAUDE_CONFIG} - If no other options are provided, this will be enabled by default",
        rich_help_panel="MCP Server Configuration"
    ),

    # Ollama Configuration
    model: str = typer.Option(
        DEFAULT_MODEL, "--model", "-m",
        help="Ollama model to use",
        rich_help_panel="Ollama Configuration"
    ),
    host: str = typer.Option(
        DEFAULT_OLLAMA_HOST, "--host", "-H",
        help="Ollama host URL",
        rich_help_panel="Ollama Configuration"
    ),

    # General Options
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        help="Show version and exit",
    )
):
    """Run the MCP Client for Ollama with specified options."""

    if version:
        typer.echo(f"mcp-client-for-ollama {__version__}")
        raise typer.Exit()

    # If none of the server arguments are provided, enable auto-discovery
    if not (mcp_server or mcp_server_url or servers_json or auto_discovery):
        auto_discovery = True

    # Run the async main function
    asyncio.run(async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host))

async def async_main(mcp_server, mcp_server_url, servers_json, auto_discovery, model, host):
    """Asynchronous main function to run the MCP Client for Ollama"""

    console = Console()

    # Create a temporary client to check if Ollama is running
    client = MCPClient(model=model, host=host)
    if not await client.model_manager.check_ollama_running():
        console.print(Panel(
            "[bold red]Error: Ollama is not running![/bold red]\n\n"
            "This client requires Ollama to be running to process queries.\n"
            "Please start Ollama by running the 'ollama serve' command in a terminal.",
            title="Ollama Not Running", border_style="red", expand=False
        ))
        return

    # Handle server configuration options - only use one source to prevent duplicates
    config_path = None
    auto_discovery_final = auto_discovery

    if servers_json:
        # If --servers-json is provided, use that and disable auto-discovery
        if os.path.exists(servers_json):
            config_path = servers_json
        else:
            console.print(f"[bold red]Error: Specified JSON config file not found: {servers_json}[/bold red]")
            return
    elif auto_discovery:
        # If --auto-discovery is provided, use that and set config_path to None
        auto_discovery_final = True
        if os.path.exists(DEFAULT_CLAUDE_CONFIG):
            console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
        else:
            console.print(f"[yellow]Warning: Claude config not found at {DEFAULT_CLAUDE_CONFIG}[/yellow]")
    else:
        # If neither is provided, check if DEFAULT_CLAUDE_CONFIG exists and use auto_discovery
        if not mcp_server and not mcp_server_url:
            if os.path.exists(DEFAULT_CLAUDE_CONFIG):
                console.print(f"[cyan]Auto-discovering servers from Claude's config at {DEFAULT_CLAUDE_CONFIG}[/cyan]")
                auto_discovery_final = True
            else:
                console.print("[yellow]Warning: No servers specified and Claude config not found.[/yellow]")

    # Validate mcp-server paths exist
    if mcp_server:
        for server_path in mcp_server:
            if not os.path.exists(server_path):
                console.print(f"[bold red]Error: Server script not found: {server_path}[/bold red]")
                return
    try:
        await client.connect_to_servers(mcp_server, mcp_server_url, config_path, auto_discovery_final)
        client.auto_load_default_config()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    app()
