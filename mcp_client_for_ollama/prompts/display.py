"""Display utilities for MCP prompts"""
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


def format_args_indicator(arguments: List[Any]) -> str:
    """Format argument indicator for prompt display

    Args:
        arguments: List of PromptArgument objects

    Returns:
        String indicator like "(code: Code to review, lang)" or "" if no args
    """
    if not arguments:
        return ""

    required_parts = []
    optional_parts = []

    for arg in arguments:
        arg_name = arg.name
        arg_desc = getattr(arg, 'description', '')
        is_required = getattr(arg, 'required', False)

        # Format: "name: description" or just "name" if no description
        if arg_desc and arg_desc != arg_name:
            formatted = f"{arg_name}: {arg_desc}"
        else:
            formatted = arg_name

        if is_required:
            required_parts.append(formatted)
        else:
            optional_parts.append(formatted)

    parts = []
    if required_parts:
        parts.append(f"requires: {', '.join(required_parts)}")
    if optional_parts:
        parts.append(f"optional: {', '.join(optional_parts)}")

    return f"({'; '.join(parts)})" if parts else ""


def display_prompt_preview(console: Console, prompt_name: str, server: str,
                          messages: List[dict], skipped_types: List[str]):
    """Display prompt preview before injection

    Args:
        console: Rich console instance
        prompt_name: Name of the prompt
        server: Server name providing the prompt
        messages: List of filtered message dicts with 'role' and 'content'
        skipped_types: List of skipped content types
    """
    title = f"[bold white]📋 Prompt: [cyan]{prompt_name}[/cyan] (server: [orange3]{server})[/orange3][/bold white]"

    content = Text()

    # Show warning if content was skipped
    if skipped_types:
        content.append("\n⚠️  Note: ", style="yellow bold")
        content.append("Skipped non-text content types: ", style="yellow")
        content.append(", ".join(skipped_types), style="yellow bold")
        content.append("\nMake sure your prompt makes sense without this content.\n", style="yellow")
        content.append("(Support for images, audio, and resources coming in a future version)\n\n", style="dim yellow")

    # Show messages count
    content.append(f"\nThis prompt will inject {len(messages)} message(s):\n\n", style="bold white")

    # Display each message with role
    for i, msg in enumerate(messages):
        role = msg['role']
        text = msg['content']

        # Truncate long messages for preview
        preview_text = text[:200] + "..." if len(text) > 200 else text

        role_style = "green" if role == "user" else "blue"
        content.append(f"[{role}] ", style=f"{role_style} bold")
        content.append(preview_text + "\n", style=role_style)

        if i < len(messages) - 1:
            content.append("\n")

    console.print()
    console.print(Panel(content, title=title, border_style="cyan", expand=False))


def display_prompt_list(console: Console, prompts_by_server: Dict[str, List[Dict[str, Any]]]):
    """Display list of all available prompts grouped by server

    Args:
        console: Rich console instance
        prompts_by_server: Dict mapping server name to list of prompt info dicts
    """
    if not prompts_by_server:
        console.print("[yellow]No prompts available from connected servers.[/yellow]")
        return

    total_prompts = sum(len(prompts) for prompts in prompts_by_server.values())

    console.print(f"\n[bold cyan]Available Prompts ({total_prompts}):[/bold cyan]\n")

    for server_name, prompts in sorted(prompts_by_server.items()):
        if not prompts:
            continue

        console.print(f"[bold green]Server: {server_name}[/bold green] ({len(prompts)} prompt(s))")

        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        table.add_column("Name", style="yellow")
        table.add_column("Arguments", style="magenta")
        table.add_column("Description", style="white")

        for prompt in prompts:
            # Access arguments directly (they are PromptArgument objects, not dicts)
            arguments = prompt.get('arguments', [])
            args_indicator = format_args_indicator(arguments)
            description = prompt.get('description', '') or ''
            # Truncate long descriptions
            if len(description) > 60:
                description = description[:57] + "..."

            table.add_row(
                f"/{prompt['name']}",
                args_indicator,
                description
            )

        console.print(table)
        console.print()

    console.print("[dim]Tip: Use /prompt_name to invoke a prompt, or type / to see autocomplete[/dim]")
