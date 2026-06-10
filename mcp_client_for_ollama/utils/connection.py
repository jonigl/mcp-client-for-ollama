"""Utility to test connectivity"""
from typing import Any, Optional

from rich.panel import Panel
import urllib.request
import urllib.error

from any_llm import AnyLLM

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
    preflight_provider = client.provider
    preflight_api_key = client.api_key

    if cli_host is None and client.config_manager.config_exists("default"):
        default_config = client.config_manager.load_configuration("default")
        config_host = default_config.get("host")
        if config_host:
            preflight_host = config_host
        config_provider = default_config.get("provider")
        if config_provider:
            preflight_provider = config_provider
        config_api_key = default_config.get("apiKey")
        if config_api_key:
            preflight_api_key = config_api_key

    if preflight_host != client.host or preflight_provider != client.provider:
        client.host = preflight_host
        client.provider = preflight_provider
        client.api_key = preflight_api_key
        client.llm = AnyLLM.create(preflight_provider, api_key=preflight_api_key, api_base=preflight_host)
        client.model_manager.llm = client.llm
        client.model_manager.provider = preflight_provider
        client.model_manager.api_base = preflight_host
        client.model_manager.api_key = preflight_api_key

    is_running = await client.model_manager.check_ollama_running()
    if not is_running:
        client.console.print(Panel(
            "[bold red]Error: Cannot connect to the LLM provider![/bold red]\n\n"
            f"[yellow]Current configured host: {client.host}[/yellow]\n"
            f"[yellow]Current provider: {client.provider}[/yellow]\n\n"
            "Possible causes:\n"
            "• LLM provider is not running or unreachable\n"
            "• Incorrect host/port configuration\n"
            "• Invalid API key\n\n"
            "Solutions:\n"
            "• For local Ollama: start it with [bold cyan]ollama serve[/bold cyan]\n"
            "• Use [bold cyan]--host[/bold cyan] flag to specify a different host\n"
            "• Use [bold cyan]--provider[/bold cyan] and [bold cyan]--api-key[/bold cyan] for remote providers",
            title="LLM Provider Not Available", border_style="red", expand=False
        ))

    return is_running
