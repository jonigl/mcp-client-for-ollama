"""Utility to test connectivity"""
from typing import Any, Optional

from rich.panel import Panel
import urllib.request
import urllib.error

from ..providers import build_llm_client, get_provider_name_for_host, is_atlascloud_host

def check_url_connectivity(url):
    """
    Check the connectivity of a URL by performing GET and POST requests.
    """
    try:
        # Test GET
        urllib.request.urlopen(url, timeout=2)

        # Test POST (empty data)
        req = urllib.request.Request(url, data=b'', method='POST')
        urllib.request.urlopen(req, timeout=2)

        return True

    except urllib.error.HTTPError:
        # Server responded with an HTTP error code (like 406, 404, 500, etc.)
        # This means the server is reachable, so return True
        return True
    except (urllib.error.URLError, OSError):
        # Skip URLs that are unreachable or timeout
        return False


async def preflight_ollama(client: Any, cli_host: Optional[str] = None) -> bool:
    """Resolve preflight host and check provider availability.

    Host resolution order:
    1) CLI host (`cli_host`) if provided
    2) default saved config host (if present)
    3) current client host

    This function mutates `client.host`, `client.ollama`, and
    `client.model_manager.ollama` when host resolution changes.

    Args:
        client: MCPClient-like object with config/model manager members.
        cli_host: Optional host provided from CLI args.

    Returns:
        bool: True when the configured provider is reachable, otherwise False.
    """
    preflight_host = cli_host if cli_host is not None else client.host

    if cli_host is None and client.config_manager.config_exists("default"):
        default_config = client.config_manager.load_configuration("default")
        config_host = default_config.get("host")
        if config_host:
            preflight_host = config_host

    if preflight_host != client.host:
        client.host = preflight_host
        client.ollama = build_llm_client(preflight_host)
        client.model_manager.ollama = client.ollama

    is_running = await client.model_manager.check_ollama_running()
    if not is_running:
        provider_name = get_provider_name_for_host(client.host)
        client.console.print(Panel(
            f"[bold red]Error: {provider_name} is unavailable![/bold red]\n\n"
            f"[yellow]{provider_name} current configured host: {client.host}[/yellow]\n\n"
            f"This client requires {provider_name} to be reachable to process queries.\n\n"
            + (
                "Please start Ollama by running the 'ollama serve' command in a terminal.\n\n"
                if not is_atlascloud_host(client.host)
                else "Please verify your Atlas Cloud API key, host URL, and network access.\n\n"
            )
            + "💡 [bold magenta]Tip:[/bold magenta] If you configured a different host in a saved default configuration you can\n\n"
            + "   1. Use --host flag to override the configured host for example: ollmcp --host http://localhost:11434\n"
            + "   2. Once done, you can save a new default configuration to avoid needing to specify it each time.",
            title=f"{provider_name} Unavailable", border_style="red", expand=False
        ))

    return is_running
