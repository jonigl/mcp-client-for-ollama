import argparse
import asyncio
import os
from contextlib import AsyncExitStack
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import ollama
from ollama import ChatResponse

from . import __version__
from .config.manager import ConfigManager 
from .utils.version import check_for_updates
from .utils.constants import DEFAULT_CLAUDE_CONFIG, TOKEN_COUNT_PER_CHAR, DEFAULT_MODEL, DEFAULT_OLLAMA_HOST
from .server.connector import ServerConnector
from .models.manager import ModelManager
from .tools.manager import ToolManager
from .utils.streaming import StreamingManager

class MCPClient:
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
        # Initialize the tool manager with server connector reference
        self.tool_manager = ToolManager(console=self.console, server_connector=self.server_connector)
        # Initialize the streaming manager
        self.streaming_manager = StreamingManager(console=self.console)
        # Store server and tool data
        self.sessions = {}  # Dict to store multiple sessions
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
        self.tool_manager.display_available_tools()
    
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
        
        # Set up the tool manager with the available tools and their enabled status
        self.tool_manager.set_available_tools(available_tools)
        self.tool_manager.set_enabled_tools(enabled_tools)

    def select_tools(self):
        """Let the user select which tools to enable using interactive prompts with server-based grouping"""
        # Save original states
        original_states = self.tool_manager.get_enabled_tools().copy()
        
        # Call the tool manager's select_tools method
        self.tool_manager.select_tools(clear_console_func=self.clear_console)
        
        
        # Display the chat history and current state after selection
        self._display_chat_history()
        self.display_available_tools()      
        self.display_current_model()

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
        # Initial Ollama API call with the query and available tools
        stream = await self.ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            tools=available_tools            
        )
        # Process the streaming response
        response_text = ""
        tool_calls = []        
        response_text, tool_calls = await self.streaming_manager.process_streaming_response(stream)
        # Check if there are any tool calls in the response
        if len(tool_calls) > 0:
            for tool in tool_calls:
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
                
                with self.console.status(f"[cyan]Running {tool_name}...[/cyan]"):
                    result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
                
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "name": tool_name
                })            

        # Get stream response from Ollama with the tool results                                
        stream = await self.ollama.chat(
            model=model,
            messages=messages,
            stream=True,
        )
        # Process the streaming response
        response_text, _ = await self.streaming_manager.process_streaming_response(stream)

        if not response_text:
            self.console.print("[red]No response received.[/red]")
            response_text = ""

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
            update_available, current_version, latest_version = check_for_updates()
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
                    await self.process_query(query)
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
            "enabledTools": self.tool_manager.get_enabled_tools(),
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
            available_tool_names = {tool.name for tool in self.tool_manager.get_available_tools()}
            for tool_name, enabled in loaded_tools.items():
                if tool_name in available_tool_names:
                    # Update in the tool manager
                    self.tool_manager.set_tool_status(tool_name, enabled)
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
        
        # Enable all tools in the tool manager
        self.tool_manager.enable_all_tools()
        # Enable all tools in the server connector
        self.server_connector.enable_all_tools()
            
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
    model_group.add_argument("--host", default=DEFAULT_OLLAMA_HOST, help=f"Ollama host URL. Default: '{DEFAULT_OLLAMA_HOST}'")
    
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
    client = MCPClient(model=args.model, host=args.host)
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
