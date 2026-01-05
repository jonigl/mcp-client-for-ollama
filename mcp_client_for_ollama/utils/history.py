"""
Chat history management utilities for the MCP client for Ollama.

This module provides functions for displaying, exporting, and importing chat history.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text


def display_full_history(chat_history: List[Dict], console: Console) -> None:
    """Display the full chat history to the console

    Args:
        chat_history: List of chat history entries with 'query' and 'response' keys
        console: Rich console for output
    """
    if not chat_history:
        console.print("[yellow]No chat history available.[/yellow]")
        return

    console.print(Panel(
        f"[bold]Full Chat History[/bold] - {len(chat_history)} conversations",
        border_style="blue",
        expand=False
    ))

    for i, entry in enumerate(chat_history, start=1):
        console.print(f"[bold green]Query {i}:[/bold green]")
        console.print(Text(entry["query"].strip(), style="green"))
        console.print("[bold blue]Answer:[/bold blue]")
        console.print(Markdown(entry["response"].strip()))
        console.print()


def export_history(chat_history: List[Dict], console: Console, filename: Optional[str] = None) -> bool:
    """Export chat history to a JSON file

    Args:
        chat_history: List of chat history entries with 'query' and 'response' keys
        console: Rich console for output
        filename: Optional custom filename. If None, uses timestamp-based default

    Returns:
        bool: True if export was successful, False otherwise
    """
    if not chat_history:
        console.print("[yellow]No chat history to export.[/yellow]")
        return False

    # Use config directory for history exports (consistent with app config location)
    history_dir = Path.home() / ".config" / "ollmcp" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"ollmcp_chat_history_{timestamp}.json"

    # Ensure .json extension
    if not filename.endswith('.json'):
        filename += '.json'

    filepath = history_dir / filename

    # Check if file already exists
    if filepath.exists():
        console.print(f"⚠️ File already exists: [cyan]{filepath}[/cyan]")
        console.print("[yellow]Please use a different filename to avoid overwriting.[/yellow]")
        return False

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓[/green] Chat history exported successfully to:")
        console.print(f"  [cyan]{filepath}[/cyan]")
        console.print(f"  ({len(chat_history)} conversations)")
        return True

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to export chat history: {str(e)}")
        return False


def import_history(filepath: str, console: Console) -> Optional[List[Dict]]:
    """Import chat history from a JSON file

    Args:
        filepath: Path to the JSON file to import
        console: Rich console for output

    Returns:
        List[Dict]: Loaded and validated chat history, or None if import failed
    """
    # Expand user path
    filepath = os.path.expanduser(filepath)

    # Check if file exists
    if not os.path.exists(filepath):
        console.print(f"[red]✗[/red] File not found: [cyan]{filepath}[/cyan]")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if not isinstance(data, list):
            console.print("[red]✗[/red] Invalid history file: Expected a list of conversations")
            return None

        # Validate each entry
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                console.print(f"[red]✗[/red] Invalid entry at position {i+1}: Expected a dictionary")
                return None

            if 'query' not in entry or 'response' not in entry:
                console.print(f"[red]✗[/red] Invalid entry at position {i+1}: Missing 'query' or 'response' key")
                return None

            if not isinstance(entry['query'], str) or not isinstance(entry['response'], str):
                console.print(f"[red]✗[/red] Invalid entry at position {i+1}: 'query' and 'response' must be strings")
                return None

        console.print(f"[green]✓[/green] Chat history imported successfully:")
        console.print(f"  [cyan]{filepath}[/cyan]")
        console.print(f"  ({len(data)} conversations)")
        return data

    except json.JSONDecodeError as e:
        console.print(f"[red]✗[/red] Invalid JSON file: {str(e)}")
        return None
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to import chat history: {str(e)}")
        return None
