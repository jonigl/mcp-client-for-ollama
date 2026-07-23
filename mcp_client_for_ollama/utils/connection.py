"""Utility to test connectivity and provider validation"""
from typing import Any

from rich.console import Console
from rich.panel import Panel

from any_llm import AnyLLM
from any_llm.exceptions import UnsupportedProviderError
from any_llm.providers.openai.base import BaseOpenAIProvider

from .constants import SUPPORTED_PROVIDERS


def validate_provider(provider: str, console: Console) -> bool:
    """Validate that a provider is known and supported by ollmcp.

    Returns True if the provider is usable, False otherwise (after printing
    a user-facing error panel).
    """
    try:
        provider_class = AnyLLM.get_provider_class(provider)
    except UnsupportedProviderError:
        console.print() # newline for spacing
        console.print(Panel(
            f"[bold red]Unknown provider:[/bold red] [bold blue]{provider}[/bold blue] is not a valid provider name.\n\n"
            f"Currently supported: {SUPPORTED_PROVIDERS}.\n\n"
            f"[dim]More providers coming soon.[/dim]",
            title="Unknown Provider", border_style="red", expand=False
        ))
        return False
    except ImportError:
        provider_class = None

    if provider_class is None or (provider != "ollama" and not issubclass(provider_class, BaseOpenAIProvider)):
        console.print() # newline for spacing
        console.print(Panel(
            f"[bold yellow]Provider not available yet:[/bold yellow] [bold blue]{provider}[/bold blue] isn't supported by ollmcp yet.\n\n"
            f"Currently supported: {SUPPORTED_PROVIDERS}.\n\n"
            f"[dim]More providers coming soon.[/dim]",
            title="Provider Not Supported", border_style="yellow", expand=False
        ))
        return False

    return True


async def preflight_ollama(client: Any) -> bool:
    """Check that the client's configured LLM provider is reachable.

    The provider, host, and API key are already resolved on the client before
    this runs, so this only performs the reachability check and renders a
    provider-appropriate error panel when it fails.

    Args:
        client: MCPClient-like object with a `model_manager` member.

    Returns:
        bool: True when the provider is reachable, otherwise False.
    """
    is_running = await client.model_manager.check_ollama_running()
    if not is_running:
        if client.provider == "ollama":
            client.console.print(Panel(
                "[bold red]Error: Cannot connect to Ollama![/bold red]\n\n"
                f"[yellow]Configured host: {client.host}[/yellow]\n\n"
                "Possible causes:\n"
                "• Ollama is not running or unreachable\n"
                "• Incorrect host/port configuration\n\n"
                "Solutions:\n"
                "• Start it with [bold cyan]ollama serve[/bold cyan]\n"
                "• Use [bold cyan]--host[/bold cyan] to point at a different Ollama host\n"
                "• Use [bold cyan]--provider[/bold cyan] and [bold cyan]--api-key[/bold cyan] for a remote provider",
                title="Ollama Not Available", border_style="red", expand=False
            ))
        else:
            host_line = f"[yellow]API base URL: {client.host}[/yellow]\n\n" if client.host else ""
            client.console.print(Panel(
                f"[bold red]Error: Cannot reach the {client.provider} provider![/bold red]\n\n"
                f"{host_line}"
                "Possible causes:\n"
                "• Invalid or missing API key\n"
                "• Network/connectivity issue\n"
                "• Wrong API base URL\n\n"
                "Solutions:\n"
                "• Check your [bold cyan]--api-key[/bold cyan] / [bold cyan]$OLLMCP_API_KEY[/bold cyan]\n"
                "• Use [bold cyan]--host[/bold cyan] to override the API base URL if needed\n"
                "• Verify the provider name and that its package is installed",
                title="LLM Provider Not Available", border_style="red", expand=False
            ))

    return is_running
