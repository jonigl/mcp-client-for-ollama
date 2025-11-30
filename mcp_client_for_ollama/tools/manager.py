"""Tool management for MCP Client for Ollama.

This module handles enabling, disabling, and selecting tools from MCP servers.
"""

import json
from typing import Dict, List, Optional, Tuple, Callable
from mcp import Tool
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.syntax import Syntax

class ToolManager:
    """Manages MCP tools.

    This class handles enabling and disabling tools, selecting tools through
    an interactive interface, and organizing tools by server.
    """

    def __init__(self, console: Optional[Console] = None, server_connector=None, model_config_manager=None):
        """Initialize the ToolManager.

        Args:
            console: Rich console for output (optional)
            server_connector: Server connector to notify of tool state changes (optional)
            model_config_manager: Model config manager to modify model settings (optional)
        """
        self.console = console or Console()
        self.available_tools = []
        self.enabled_tools = {}
        self.server_connector = server_connector
        self.model_config_manager = model_config_manager
        self._create_builtin_tools()

    def _create_builtin_tools(self):
        """Create and register built-in tools."""
        if not self.model_config_manager:
            return

        set_prompt_tool = Tool(
            name="builtin.set_system_prompt",
            description="Update the system prompt for the assistant. Use this to change your instructions or persona.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The new system prompt. Use a concise and clear prompt to define the persona and instructions for the AI assistant."
                    }
                },
                "required": ["prompt"]
            }
        )
        
        get_prompt_tool = Tool(
            name="builtin.get_system_prompt",
            description="Get the current system prompt for the assistant.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        )

        self.available_tools.append(set_prompt_tool)
        self.available_tools.append(get_prompt_tool)
        # Enable them by default
        self.enabled_tools[set_prompt_tool.name] = True
        self.enabled_tools[get_prompt_tool.name] = True

    def set_available_tools(self, tools: List[Tool]) -> None:
        """Set the available tools from servers, preserving built-in tools.

        Args:
            tools: List of available tools from servers
        """
        # Filter out any existing non-builtin tools, keeping the built-in ones that were added during initialization.
        self.available_tools = [t for t in self.available_tools if t.name.startswith('builtin.')]
        # Add the new tools from the server.
        self.available_tools.extend(tools)

    def set_enabled_tools(self, server_enabled_tools: Dict[str, bool]) -> None:
        """Set the enabled status of tools from servers, preserving built-in tool statuses.

        Args:
            server_enabled_tools: Dictionary mapping tool names to enabled status from servers
        """
        # Preserve the enabled status of built-in tools that were set during init
        builtin_enabled = {
            name: status for name, status in self.enabled_tools.items() if name.startswith('builtin.')
        }

        # The new state is the server tools...
        self.enabled_tools = server_enabled_tools
        # ...updated with the built-in tools.
        self.enabled_tools.update(builtin_enabled)

        # Notify server connector of tool status changes for ONLY the server tools
        self._notify_server_connector_batch(server_enabled_tools)

    # Helper methods for common operations
    def _notify_server_connector(self, tool_name: str, enabled: bool) -> None:
        """Notify the server connector of a tool status change.

        Args:
            tool_name: Name of the tool that changed
            enabled: New status of the tool
        """
        if self.server_connector:
            self.server_connector.set_tool_status(tool_name, enabled)

    def _notify_server_connector_batch(self, tool_status: Dict[str, bool]) -> None:
        """Notify the server connector of multiple tool status changes.

        Args:
            tool_status: Dictionary mapping tool names to enabled status
        """
        if self.server_connector:
            for tool_name, enabled in tool_status.items():
                self.server_connector.set_tool_status(tool_name, enabled)

    def _clear_console(self, clear_console_func: Optional[Callable]) -> None:
        """Clear the console if a clear function is provided.

        Args:
            clear_console_func: Function to clear the console
        """
        if clear_console_func:
            clear_console_func()

    def _get_status_indicator(self, enabled: bool) -> str:
        """Get a formatted status indicator based on enabled state.

        Args:
            enabled: Whether the item is enabled

        Returns:
            Formatted string with colored checkmark or X
        """
        return "[green]✓[/green]" if enabled else "[red]✗[/red]"

    # Rest of the original methods with improvements
    def get_available_tools(self) -> List[Tool]:
        """Get the list of available tools.

        Returns:
            List of available tools
        """
        return self.available_tools

    def get_enabled_tools(self) -> Dict[str, bool]:
        """Get the dictionary of tool enabled status.

        Returns:
            Dictionary mapping tool names to enabled status
        """
        return self.enabled_tools

    def enable_all_tools(self) -> None:
        """Enable all available tools."""
        for tool in self.available_tools:
            self.enabled_tools[tool.name] = True

        # Also update the server connector if available
        if self.server_connector:
            self.server_connector.enable_all_tools()

    def disable_all_tools(self) -> None:
        """Disable all available tools."""
        tool_status_updates = {}

        for tool in self.available_tools:
            self.enabled_tools[tool.name] = False
            tool_status_updates[tool.name] = False

        # Notify server connector of all changes at once
        self._notify_server_connector_batch(tool_status_updates)

    def set_tool_status(self, tool_name: str, enabled: bool) -> None:
        """Set the enabled status of a specific tool.

        Args:
            tool_name: Name of the tool to modify
            enabled: Whether the tool should be enabled
        """
        if tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = enabled
            self._notify_server_connector(tool_name, enabled)

    def display_available_tools(self) -> None:
        """Display available tools with their enabled/disabled status."""
        # Create a list of styled tool names
        tool_texts = []
        enabled_count = 0
        for tool in self.available_tools:
            is_enabled = self.enabled_tools.get(tool.name, True)
            if is_enabled:
                enabled_count += 1
            status = self._get_status_indicator(is_enabled)
            tool_texts.append(f"{status} {tool.name}")

        # Display tools in columns for better readability
        if tool_texts:
            columns = Columns(tool_texts, equal=True, expand=True)
            subtitle = f"[bold]{enabled_count}/{len(self.available_tools)} tools enabled[/bold]"
            self.console.print(Panel(columns, title="[bold]🔧 Available Tools[/bold]", subtitle=subtitle, border_style="green"))
        else:
            self.console.print("[yellow]No tools available from the server[/yellow]")

    # These helper methods break down the select_tools method into more manageable pieces
    def _display_tool_selection_header(self) -> None:
        """Display the tool selection header."""
        self.console.print(Panel(Text.from_markup("[bold]🔧 Tool Selection[/bold]", justify="center"),
                                 expand=True, border_style="green"))
        self.console.print(Panel("[bold]Available Servers and Tools[/bold]",
                                 border_style="blue", expand=False))

    def _display_server_tools(self, server_name: str, server_idx: int, server_tools: List[Tool],
                             show_descriptions: bool, index_to_tool: Dict[int, Tool],
                             tool_index: int) -> int:
        """Display tools for a specific server and update the tool index.

        Args:
            server_name: Name of the server
            server_idx: Index of the server
            server_tools: List of tools for this server
            show_descriptions: Whether to show tool descriptions
            index_to_tool: Mapping from display index to tool object
            tool_index: Current tool index

        Returns:
            Updated tool index after processing all tools
        """
        enabled_count = sum(1 for tool in server_tools if self.enabled_tools[tool.name])
        total_count = len(server_tools)

        # Determine server status indicator
        if enabled_count == total_count:
            server_status = self._get_status_indicator(True)  # All enabled
        elif enabled_count == 0:
            server_status = self._get_status_indicator(False)  # None enabled
        else:
            server_status = "[yellow]~[/yellow]"  # Some enabled

        # Create panel title with server number, status and name
        display_server_name = "Built-in Tools" if server_name == "builtin" else server_name
        panel_title = f"[bold orange3]S{server_idx+1}. {server_status} {display_server_name}[/bold orange3]"
        # Create panel subtitle with tools count
        panel_subtitle = f"[green]{enabled_count}/{total_count} tools enabled[/green]"

        # Different display mode based on whether descriptions are shown
        if show_descriptions:
            # Simple list format for when descriptions are shown
            tool_list = []
            for tool in server_tools:
                status = self._get_status_indicator(self.enabled_tools[tool.name])
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
                status = self._get_status_indicator(self.enabled_tools[tool.name])
                tool_text = f"[magenta]{tool_index}[/magenta]. {status} {tool.name}"

                # Store the mapping from display index to tool
                index_to_tool[tool_index] = tool
                tool_index += 1

                server_tool_texts.append(tool_text)

            # Display tools in columns inside a panel if there are any
            if server_tool_texts:
                columns = Columns(server_tool_texts, padding=(0, 2), equal=False, expand=False)
                self.console.print(Panel(columns, padding=(1,1), title=panel_title,
                                     subtitle=panel_subtitle, border_style="blue",
                                     title_align="left", subtitle_align="right"))
        return tool_index

    def _display_command_help(self, show_descriptions: bool) -> None:
        """Display the command help panel.

        Args:
            show_descriptions: Current state of description display
        """
        self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
        self.console.print("• Enter [bold magenta]numbers[/bold magenta][bold yellow] separated by commas or ranges[/bold yellow] to toggle tools (e.g. [bold]1,3,5-8[/bold])")
        self.console.print("• Enter [bold orange3]S + number[/bold orange3] to toggle all tools in a server (e.g. [bold]S1[/bold] or [bold]s2[/bold])")
        self.console.print("• [bold]a[/bold] or [bold]all[/bold] - Enable all tools")
        self.console.print("• [bold]n[/bold] or [bold]none[/bold] - Disable all tools")
        self.console.print(f"• [bold]d[/bold] or [bold]desc[/bold] - {'Hide' if show_descriptions else 'Show'} descriptions")
        self.console.print("• [bold]j[/bold] or [bold]json[/bold] - Show detailed tool JSON schemas on enabled tools for debugging purposes")
        self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save changes and return")
        self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")

    def _process_server_toggle(self, selection: str, sorted_servers: List[Tuple[str, List[Tool]]],
                              clear_console_func: Optional[Callable]) -> Tuple[Optional[str], str]:
        """Process a server toggle command.

        Args:
            selection: User selection (e.g., "s1")
            sorted_servers: List of (server_name, server_tools) tuples
            clear_console_func: Function to clear the console

        Returns:
            Tuple of (result_message, result_style)
        """
        server_idx = int(selection[1:]) - 1
        if 0 <= server_idx < len(sorted_servers):
            server_name, server_tools = sorted_servers[server_idx]

            # Check if all tools in this server are currently enabled
            all_enabled = all(self.enabled_tools[tool.name] for tool in server_tools)

            # Toggle accordingly: if all are enabled, disable all; otherwise enable all
            new_state = not all_enabled
            tool_updates = {}
            for tool in server_tools:
                self.enabled_tools[tool.name] = new_state
                tool_updates[tool.name] = new_state

            # Notify server connector of all changes
            self._notify_server_connector_batch(tool_updates)

            # Clear console and return result message
            self._clear_console(clear_console_func)
            message = f"[{'green' if new_state else 'yellow'}]All tools in server '{server_name}' {'enabled' if new_state else 'disabled'}![/{'green' if new_state else 'yellow'}]"
            style = 'green' if new_state else 'yellow'
            return message, style
        else:
            # Clear console and return error message
            self._clear_console(clear_console_func)
            message = f"[red]Invalid server number: S{server_idx+1}. Must be between S1 and S{len(sorted_servers)}[/red]"
            return message, 'red'

    def _process_tool_selection(self, selection: str, index_to_tool: Dict[int, Tool],
                               clear_console_func: Optional[Callable]) -> Tuple[Optional[str], str]:
        """Process tool selection command.

        Args:
            selection: User selection (e.g., "1,3,5-8")
            index_to_tool: Mapping from display index to tool object
            clear_console_func: Function to clear the console

        Returns:
            Tuple of (result_message, result_style)
        """
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
            tool_updates = {}

            for idx in selections:
                if idx in index_to_tool:
                    tool = index_to_tool[idx]
                    new_state = not self.enabled_tools[tool.name]
                    self.enabled_tools[tool.name] = new_state
                    tool_updates[tool.name] = new_state
                    valid_toggle = True
                    toggled_tools_count += 1
                else:
                    invalid_indices.append(idx)

            # Notify server connector of all changes
            self._notify_server_connector_batch(tool_updates)

            if valid_toggle:
                result_message = f"[green]Successfully toggled {toggled_tools_count} tool{'s' if toggled_tools_count != 1 else ''}![/green]"
                result_style = "green"
                if invalid_indices:
                    result_message += f"\n[yellow]Warning: Invalid indices ignored: {', '.join(map(str, invalid_indices))}[/yellow]"
            else:
                result_message = "[red]No valid tool numbers provided.[/red]"
                result_style = "red"

        except ValueError:
            result_message = "[red]Invalid input. Please enter numbers, ranges, or server designators.[/red]"
            result_style = "red"

        self._clear_console(clear_console_func)
        return result_message, result_style

    def select_tools(self, clear_console_func=None) -> None:
        """Interactive interface for enabling/disabling tools.

        Args:
            clear_console_func: Function to clear the console (optional)
        """
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
        self._clear_console(clear_console_func)

        while True:
            # Show the tool selection interface
            self._display_tool_selection_header()

            tool_index = 1  # Global tool index across all servers
            index_to_tool = {}  # Mapping of display indices to tools

            # Display servers and their tools
            for server_idx, (server_name, server_tools) in enumerate(sorted_servers):
                tool_index = self._display_server_tools(
                    server_name, server_idx, server_tools,
                    show_descriptions, index_to_tool, tool_index
                )
                self.console.print()  # Add space between servers

            # Display the result message if there is one
            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None  # Clear the message after displaying it

            # Display the command help
            self._display_command_help(show_descriptions)

            # Get user input
            selection = Prompt.ask("> ").strip().lower()

            # Process user commands
            if selection in ['s', 'save']:
                self._clear_console(clear_console_func)
                return

            if selection in ['q', 'quit']:
                # Restore original tool states
                self.enabled_tools = original_states.copy()
                self._clear_console(clear_console_func)
                return

            if selection in ['a', 'all']:
                self.enable_all_tools()
                self._clear_console(clear_console_func)
                result_message, result_style = "[green]All tools enabled![/green]", "green"
                continue

            if selection in ['n', 'none']:
                self.disable_all_tools()
                self._clear_console(clear_console_func)
                result_message, result_style = "[yellow]All tools disabled![/yellow]", "yellow"
                continue

            if selection in ['d', 'desc']:
                show_descriptions = not show_descriptions
                status = "shown" if show_descriptions else "hidden"
                self._clear_console(clear_console_func)
                result_message, result_style = f"[blue]Tool descriptions {status}![/blue]", "blue"
                continue

            if selection in ['j', 'json']:
                self._clear_console(clear_console_func)
                self.debug_tool_schemas()
                self.console.print("\n[dim]Press Enter to continue...[/dim]")
                input()  # Wait for user to press Enter
                self._clear_console(clear_console_func)
                continue

            # Check for server toggle (S1, S2, etc.)
            if selection.startswith('s') and len(selection) > 1 and selection[1:].isdigit():
                result_message, result_style = self._process_server_toggle(
                    selection, sorted_servers, clear_console_func
                )
                continue

            # Process individual tool selections and ranges
            result_message, result_style = self._process_tool_selection(
                selection, index_to_tool, clear_console_func
            )

    def get_enabled_tool_objects(self) -> List[Tool]:
        """Get a list of the Tool objects that are enabled.

        Returns:
            List[Tool]: List of enabled tool objects
        """
        return [tool for tool in self.available_tools if self.enabled_tools.get(tool.name, False)]

    def set_server_connector(self, server_connector):
        """Set the server connector to notify of tool state changes.

        Args:
            server_connector: The server connector instance
        """
        self.server_connector = server_connector

    def debug_tool_schemas(self) -> None:
        """Debug method to display detailed tool schemas"""
        enabled_tools = self.get_enabled_tool_objects()

        if not enabled_tools:
            self.console.print("[yellow]No tools are enabled.[/yellow]")
            return

        self.console.print(Panel("[bold]🔍 Tool Schema Debug Information[/bold]", border_style="cyan"))

        for tool in enabled_tools:
            # Tool header
            tool_panel = Panel(
                f"{tool.description or 'No description'}",
                title=f"{tool.name} Info",
                border_style="green",
                padding=(1, 1)
            )
            self.console.print(tool_panel)

            # Schema content with JSON syntax highlighting
            try:
                schema_json = json.dumps(tool.inputSchema, indent=2)
                syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=False)
                schema_panel = Panel(
                    syntax,
                    title=f"[bold orange3]{tool.name} Input Schema[bold orange3]",
                    border_style="blue"
                )
                self.console.print(schema_panel)
            except Exception as e:
                error_panel = Panel(
                    f"[red]Error: {str(e)}[/red]\n[yellow]Raw: {tool.inputSchema}[/yellow]",
                    title="Schema Error",
                    border_style="red"
                )
                self.console.print(error_panel)

            self.console.print()  # Add spacing between tools
