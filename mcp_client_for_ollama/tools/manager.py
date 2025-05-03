"""Tool management for MCP Client for Ollama.

This module handles enabling, disabling, and selecting tools from MCP servers.
"""

from typing import Dict, List, Any, Optional, Tuple
from mcp import Tool
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

class ToolManager:
    """Manages MCP tools.
    
    This class handles enabling and disabling tools, selecting tools through
    an interactive interface, and organizing tools by server.
    """
    
    def __init__(self, console: Optional[Console] = None, server_connector=None):
        """Initialize the ToolManager.
        
        Args:
            console: Rich console for output (optional)
            server_connector: Server connector to notify of tool state changes (optional)
        """
        self.console = console or Console()
        self.available_tools = []
        self.enabled_tools = {}
        self.server_connector = server_connector
        
    def set_available_tools(self, tools: List[Tool]) -> None:
        """Set the available tools.
        
        Args:
            tools: List of available tools
        """
        self.available_tools = tools
        
    def set_enabled_tools(self, enabled_tools: Dict[str, bool]) -> None:
        """Set the enabled status of tools.
        
        Args:
            enabled_tools: Dictionary mapping tool names to enabled status
        """
        self.enabled_tools = enabled_tools
        
        # Also update the server connector if available
        if self.server_connector:
            for tool_name, enabled in enabled_tools.items():
                self.server_connector.set_tool_status(tool_name, enabled)
        
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
        for tool in self.available_tools:
            self.enabled_tools[tool.name] = False
            
        # Also update the server connector if available
        if self.server_connector:
            for tool in self.available_tools:
                self.server_connector.set_tool_status(tool.name, False)
            
    def set_tool_status(self, tool_name: str, enabled: bool) -> None:
        """Set the enabled status of a specific tool.
        
        Args:
            tool_name: Name of the tool to modify
            enabled: Whether the tool should be enabled
        """
        if tool_name in self.enabled_tools:
            self.enabled_tools[tool_name] = enabled
            
            # Also update the server connector if available
            if self.server_connector:
                self.server_connector.set_tool_status(tool_name, enabled)
    
    def display_available_tools(self) -> None:
        """Display available tools with their enabled/disabled status."""
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
        if clear_console_func:
            clear_console_func()
        
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
                if clear_console_func:
                    clear_console_func()
                return
            
            if selection in ['q', 'quit']:
                # Restore original tool states
                self.enabled_tools = original_states.copy()
                if clear_console_func:
                    clear_console_func()
                return
            
            if selection in ['a', 'all']:
                self.enable_all_tools()
                if clear_console_func:
                    clear_console_func()
                result_message = "[green]All tools enabled![/green]"                
                continue
            
            if selection in ['n', 'none']:
                self.disable_all_tools()
                if clear_console_func:
                    clear_console_func()
                result_message = "[yellow]All tools disabled![/yellow]"                
                continue
                
            if selection in ['d', 'desc']:
                show_descriptions = not show_descriptions
                if clear_console_func:
                    clear_console_func()
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
                    
                    if clear_console_func:
                        clear_console_func()
                    status = "enabled" if new_state else "disabled"
                    result_message = f"[{'green' if new_state else 'yellow'}]All tools in server '{server_name}' {status}![/{'green' if new_state else 'yellow'}]"                    
                else:
                    if clear_console_func:
                        clear_console_func()
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
                        valid_toggle = True
                        toggled_tools_count += 1
                    else:
                        invalid_indices.append(idx)
                
                if clear_console_func:
                    clear_console_func()
                if valid_toggle:
                    result_message = f"[green]Successfully toggled {toggled_tools_count} tool{'s' if toggled_tools_count != 1 else ''}![/green]"
                    if invalid_indices:
                        result_message += f"\n[yellow]Warning: Invalid indices ignored: {', '.join(map(str, invalid_indices))}[/yellow]"
                else:
                    result_message = "[red]No valid tool numbers provided.[/red]"
                    result_style = "red"
            
            except ValueError:
                if clear_console_func:
                    clear_console_func()
                result_message = "[red]Invalid input. Please enter numbers, ranges, or server designators.[/red]"
                result_style = "red"
    
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
