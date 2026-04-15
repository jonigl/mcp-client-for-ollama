"""Utility to test connectivity"""
from typing import Any, Optional

import ollama
from rich.panel import Panel
import urllib.request
import urllib.error

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
    """Resolve preflight host and check Ollama availability.

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
        bool: True when Ollama is reachable, otherwise False.
    """
    preflight_host = cli_host if cli_host is not None else client.host

    if cli_host is None and client.config_manager.config_exists("default"):
        default_config = client.config_manager.load_configuration("default")
        config_host = default_config.get("host")
        if config_host:
            preflight_host = config_host

    if preflight_host != client.host:
        client.host = preflight_host
        client.ollama = ollama.AsyncClient(host=preflight_host)
        client.model_manager.ollama = client.ollama

    is_running = await client.model_manager.check_ollama_running()
    if not is_running:
        client.console.print(Panel(
            "[bold red]Error: Ollama is not running![/bold red]\n\n"
            f"[yellow]Ollama current configured host: {client.host}[/yellow]\n\n"
            "This client requires Ollama to be running to process queries.\n\n"
            "Please start Ollama by running the 'ollama serve' command in a terminal.\n\n"
            "💡 [bold magenta]Tip:[/bold magenta] If you configured a different host in a saved default configuration you can\n\n"
            "   1. Use --host flag to override the configured host for example: ollmcp --host http://localhost:11434\n"
            "   2. Once done, you can save a new default configuration to avoid needing to specify it each time.",
            title="Ollama Not Running", border_style="red", expand=False
        ))

    return is_running
