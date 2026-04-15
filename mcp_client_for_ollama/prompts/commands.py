"""Slash command execution utilities for interactive chat."""

from typing import Any

from ..utils.history import display_full_history, export_history, import_history
from ..utils.input import get_input_no_autocomplete


async def run_slash_command(client: Any, command_name: str) -> bool:
    """Execute a slash command by canonical name.

    Args:
        client: MCP client instance handling the interactive session.
        command_name: Canonical slash command name.

    Returns:
        bool: True to continue the chat loop, False to exit.
    """
    if command_name == 'quit':
        client.console.print("[yellow]Exiting...[/yellow]")
        return False

    if command_name == 'tools':
        client.select_tools()
        return True

    if command_name == 'help':
        client.print_help()
        return True

    if command_name == 'model':
        await client.select_model()
        return True

    if command_name == 'model-config':
        client.configure_model_options()
        return True

    if command_name == 'context':
        client.toggle_context_retention()
        return True

    if command_name == 'thinking-mode':
        await client.toggle_thinking_mode()
        return True

    if command_name == 'show-thinking':
        await client.toggle_show_thinking()
        return True

    if command_name == 'loop-limit':
        await client.set_loop_limit()
        return True

    if command_name == 'show-tool-execution':
        client.toggle_show_tool_execution()
        return True

    if command_name == 'show-metrics':
        client.toggle_show_metrics()
        return True

    if command_name == 'clear':
        client.clear_context()
        return True

    if command_name == 'context-info':
        client.display_context_stats()
        return True

    if command_name == 'clear-screen':
        client.clear_console()
        client.display_available_tools()
        client.display_current_model()
        return True

    if command_name == 'save-config':
        config_name = await get_input_no_autocomplete("Config name (or press Enter for default)")
        if not config_name or config_name.strip() == "":
            config_name = "default"
        client.save_configuration(config_name)
        return True

    if command_name == 'load-config':
        config_name = await get_input_no_autocomplete("Config name to load (or press Enter for default)")
        if not config_name or config_name.strip() == "":
            config_name = "default"
        client.load_configuration(config_name)
        client.display_available_tools()
        client.display_current_model()
        return True

    if command_name == 'reset-config':
        client.reset_configuration()
        client.display_available_tools()
        client.display_current_model()
        return True

    if command_name == 'reload-servers':
        await client.reload_servers()
        return True

    if command_name == 'human-in-the-loop':
        client.hil_manager.toggle()
        return True

    if command_name == 'prompts':
        client.browse_prompts()
        return True

    if command_name == 'full-history':
        display_full_history(client.chat_history, client.console)
        return True

    if command_name == 'export-history':
        filename = await get_input_no_autocomplete("Export filename (or press Enter for default)")
        if not filename or filename.strip() == "":
            export_history(client.chat_history, client.console)
        else:
            export_history(client.chat_history, client.console, filename.strip())
        return True

    if command_name == 'import-history':
        filepath = await get_input_no_autocomplete("Path to history file to import")
        if filepath and filepath.strip():
            imported = import_history(filepath.strip(), client.console)
            if imported is not None:
                client.chat_history = imported
                client.console.print("[green]Current chat history replaced with imported history.[/green]")
        else:
            client.console.print("[yellow]Import cancelled: No filepath provided.[/yellow]")
        return True

    # parse_user_input() only routes canonical command names here.
    raise AssertionError(f"Unhandled slash command: {command_name}")
