"""Model management for MCP Client for Ollama.

This module handles listing, selecting, and managing Ollama models.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from ..utils.constants import DEFAULT_MODEL

class ModelManager:
    """Manages Ollama models.

    This class handles listing available models from Ollama, checking if
    Ollama is running, and selecting models to use with the client.
    """

    def __init__(self, console: Optional[Console] = None, default_model: str = DEFAULT_MODEL, llm: Optional[Any] = None, provider: str = "ollama", api_base: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the ModelManager.

        Args:
            console: Rich console for output (optional)
            default_model: Default model to use if none is specified
            llm: AnyLLM instance for provider access
            provider: Provider name (e.g. 'ollama', 'openai')
            api_base: Provider base URL
            api_key: Provider API key
        """
        self.console = console or Console()
        self.model = default_model
        self.llm = llm
        self.provider = provider
        self.api_base = api_base
        self.api_key = api_key
        self._capabilities_cache: Dict[str, List[str]] = {}

    async def check_ollama_running(self) -> bool:
        """Check if the LLM provider is reachable.

        Returns:
            bool: True if the provider is reachable, False otherwise
        """
        try:
            await self._list_models()
            return True
        except Exception:
            return False

    async def list_ollama_models(self) -> List[Dict[str, Any]]:
        """Get a list of available models from the provider.

        Returns:
            List[Dict[str, Any]]: List of model objects each with name and other metadata
        """
        try:
            return await self._list_models()
        except Exception as e:
            self.console.print(f"[red]Error getting models: {str(e)}[/red]")
            return []

    async def _list_models(self) -> List[Dict[str, Any]]:
        """Fetch models from the provider, returning a list of dicts with 'name' etc."""
        if self.provider == "ollama":
            return await self._ollama_list_models()
        return await self._generic_list_models()

    async def _ollama_list_models(self) -> List[Dict[str, Any]]:
        """Call ollama's native /api/tags for full model metadata."""
        base = (self.api_base or "http://localhost:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])

    async def _generic_list_models(self) -> List[Dict[str, Any]]:
        """List models via any-llm for OpenAI-compatible providers."""
        if self.llm is None:
            return []
        result = await self.llm.alist_models()
        items = result.data if hasattr(result, "data") else result
        models = []
        for m in (items or []):
            model_id = getattr(m, "id", str(m))
            created = getattr(m, "created", None)
            modified_at = (
                datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                if created else ""
            )
            models.append({"name": model_id, "model": model_id, "modified_at": modified_at, "size": 0, "digest": "", "details": {}})
        return models

    def get_current_model(self) -> str:
        """Get the currently selected model.

        Returns:
            str: Name of the current model
        """
        return self.model

    def set_model(self, model_name: str) -> None:
        """Set the current model.

        Args:
            model_name: Name of the model to set as current
        """
        self.model = model_name

    async def fetch_capabilities(self, model_name: str) -> List[str]:
        """Fetch and cache the capabilities of a model.

        Args:
            model_name: Name of the model to fetch capabilities for

        Returns:
            List[str]: List of capability strings (e.g. ['vision', 'tools', 'thinking'])
        """
        if model_name in self._capabilities_cache:
            return self._capabilities_cache[model_name]
        try:
            caps = await self._fetch_capabilities(model_name)
            self._capabilities_cache[model_name] = list(caps)
        except Exception:
            self._capabilities_cache[model_name] = []
        return self._capabilities_cache[model_name]

    async def _fetch_capabilities(self, model_name: str) -> List[str]:
        """Fetch raw capabilities for a model from the provider."""
        if self.provider == "ollama":
            return await self._ollama_fetch_capabilities(model_name)
        # For non-ollama providers, assume all capabilities are available.
        # The provider API will surface an error if a specific capability is unsupported.
        return ["tools", "vision", "thinking"]

    async def _ollama_fetch_capabilities(self, model_name: str) -> List[str]:
        """Call ollama's /api/show endpoint for real capability data."""
        base = (self.api_base or "http://localhost:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{base}/api/show", json={"name": model_name})
            resp.raise_for_status()
            return resp.json().get("capabilities", [])

    def format_capabilities_badges(self, capabilities: List[str]) -> str:
        """Format model capabilities as colored emoji+word badges.

        Args:
            capabilities: List of capability strings from Ollama

        Returns:
            str: Separated colored badge string, or empty string if no known capabilities
        """
        badge_map = [
            ("vision",   "[bold cyan]👀 Vision[/bold cyan]"),
            ("tools",    "[bold orange3]🔧 Tools[/bold orange3]"),
            ("thinking", "[bold magenta]💭 Thinking[/bold magenta]"),
        ]
        badges = [badge for cap, badge in badge_map if cap in capabilities]
        return " [dim]│[/dim] ".join(badges)

    def display_current_model(self, thinking_mode: bool = False, reasoning_effort: str = "") -> None:
        """Display the currently selected model in the console."""
        capabilities = self._capabilities_cache.get(self.model, [])
        badges = self.format_capabilities_badges(capabilities)

        # Annotate the Thinking badge with the current effort level when thinking is active
        if thinking_mode and reasoning_effort and "thinking" in capabilities:
            badges = badges.replace(
                "[bold magenta]💭 Thinking[/bold magenta]",
                f"[bold magenta]💭 Thinking ({reasoning_effort})[/bold magenta]",
            )

        content = (
            f"[bold blue]Current model:[/bold blue] [bold green]{self.model}[/bold green]"
            f" [bold yellow]({self.provider})[/bold yellow]"
        )
        if badges:
            content += f"\n[bold blue]Capabilities:[/bold blue] {badges}"
        self.console.print(Panel(content, border_style="blue", expand=False))

    def format_model_display_info(self, model: Dict[str, Any]) -> Tuple[str, str, str]:
        """Format model information for display.

        Args:
            model: Model metadata dictionary

        Returns:
            Tuple[str, str, str]: Model name, size string, and modified date string
        """
        # Extract model name, trying different fields
        model_name = model.get("name", "Unknown")
        if model_name == "Unknown":
            # Try alternative fields that might contain the name
            for key in ["name", "model", "tag", "id"]:
                if key in model and model[key]:
                    model_name = model[key]
                    break

        # Format size if available
        size = model.get("size", 0)
        size_str = f"{size/(1024*1024):.1f} MB" if size else "Unknown size"

        # Format the date if available
        modified_at = model.get("modified_at", "Unknown")
        if modified_at and modified_at != "Unknown":
            try:
                if hasattr(modified_at, "strftime"):
                    # datetime object (e.g. from non-ollama providers)
                    modified_at = modified_at.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(modified_at, str):
                    # ISO string from ollama native API — parse then format
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified_at)
                    modified_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                modified_at = "Unknown date"
        else:
            modified_at = "Unknown"

        return model_name, size_str, modified_at

    async def select_model_interactive(self, clear_console_func=None) -> str:
        """Let the user select an Ollama model from the available ones.

        Args:
            clear_console_func: Function to clear the console (optional)

        Returns:
            str: The selected model name (or the original if canceled)
        """
        # Check if Ollama is running first
        if not await self.check_ollama_running():
            self.console.print(Panel(
                "[bold red]Ollama is not running![/bold red]\n\n"
                "Please start Ollama before trying to list or switch models.\n"
                "You can start Ollama by running the 'ollama serve' command in a terminal.",
                title="Error", border_style="red", expand=False
            ))
            return self.model

        # Save the current model in case the user cancels
        original_model = self.model
        # Track currently selected model (which might not be saved yet)
        selected_model = self.model
        result_message = None
        result_style = "red"

        # Get available models and pre-fetch capabilities in parallel
        with self.console.status("[cyan]Getting available models from Ollama...[/cyan]"):
            models = await self.list_ollama_models()
            if models:
                model_names = [self.format_model_display_info(m)[0] for m in models]
                await asyncio.gather(*[self.fetch_capabilities(n) for n in model_names], return_exceptions=True)

        if not models:
            self.console.print("[yellow]No models available. Try pulling a model with 'ollama pull <model>'[/yellow]")
            return self.model

        # Main model selection loop
        while True:
            # Clear console for a clean interface
            if clear_console_func:
                clear_console_func()

            # Display model selection interface
            self.console.print(Panel(Text.from_markup("[bold]🧠 Select a Model[/bold]", justify="center"), expand=True, border_style="green"))

            # Sort models by name for easier reading
            models.sort(key=lambda m: self.format_model_display_info(m)[0])

            # Display available models as a table
            table = Table(show_header=True, header_style="bold cyan", border_style="blue", expand=False)
            table.add_column("#", style="bold magenta", width=4, justify="right")
            table.add_column("Current", justify="center")
            table.add_column("Name", style="bold blue")
            table.add_column("Size", style="dim", justify="right")
            table.add_column("Modified", style="dim")
            table.add_column("👀 Vision", justify="center")
            table.add_column("🔧 Tools", justify="center")
            table.add_column("💭 Thinking", justify="center")

            for i, model in enumerate(models):
                model_name, size_str, modified_at = self.format_model_display_info(model)
                is_current = model_name == selected_model
                indicator = "[green]→[/green]" if is_current else ""
                caps = self._capabilities_cache.get(model_name, [])
                vision   = "[green]✓[/green]" if "vision"   in caps else ""
                tools    = "[green]✓[/green]" if "tools"    in caps else ""
                thinking = "[green]✓[/green]" if "thinking" in caps else ""
                table.add_row(str(i + 1), indicator, model_name, size_str, modified_at, vision, tools, thinking)

            self.console.print(table)

            # Show current model with an indicator (this is the saved model)
            self.console.print(f"\nCurrent model: [bold green]{self.model}[/bold green]")
            if selected_model != self.model:
                self.console.print(f"Selected model: [bold yellow]{selected_model}[/bold yellow] (not saved yet)")
            self.console.print()

            # Display the result message if there is one
            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None  # Clear the message after displaying it

            # Show the command panel
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print("• Enter [bold magenta]number[/bold magenta] to select a model")
            self.console.print("• [bold]s[/bold] or [bold]save[/bold] - Save model selection and return")
            self.console.print("• [bold]q[/bold] or [bold]quit[/bold] - Cancel and return")

            selection = Prompt.ask("> ")
            selection = selection.strip().lower()

            if selection in ['s', 'save']:
                # Save the selected model as current model
                self.model = selected_model
                if clear_console_func:
                    clear_console_func()
                return self.model

            if selection in ['q', 'quit']:
                # Restore original model
                if clear_console_func:
                    clear_console_func()
                return original_model

            try:
                idx = int(selection) - 1
                if 0 <= idx < len(models):
                    # Update the selected model (but don't save it yet)
                    model_data = models[idx]
                    for key in ["name", "model", "tag", "id"]:
                        if key in model_data and model_data[key]:
                            selected_model = model_data[key]
                            break
                    else:
                        if clear_console_func:
                            clear_console_func()
                        result_message = "[red]Error: Could not determine the model name from the API response.[/red]"
                        result_style = "red"
                else:
                    if clear_console_func:
                        clear_console_func()
                    result_message = f"[red]Invalid number: {idx + 1}. Must be between 1 and {len(models)}[/red]"
                    result_style = "red"
            except ValueError:
                if clear_console_func:
                    clear_console_func()
                result_message = "[red]Invalid input. Please enter a number.[/red]"
                result_style = "red"

    async def resolve_initial_model(self, explicit_model: Optional[str], saved_model: Optional[str]) -> Optional[Any]:
        """Validate the model to use at startup against what's actually installed.

        Precedence: explicit_model (--model flag) > saved_model (saved configuration)
        > first available model (alphabetically). The highest-priority candidate that
        is actually installed wins. If a higher-priority candidate isn't installed,
        the next one down is used instead and the caller is told about it.

        Args:
            explicit_model: The model passed via --model, if the user passed one.
            saved_model: The model loaded from a saved configuration, if one existed.

        Returns:
            None if the top-priority candidate (or no candidate at all) was used as
            requested, "no-models" if Ollama has no models installed, "auto-selected"
            if no candidate was requested and the first available model was picked,
            or a (requested, used) tuple if a lower-priority candidate had to be
            substituted for an unavailable higher-priority one.
        """
        models = await self.list_ollama_models()
        if not models:
            # Keep showing whatever the user actually asked for (even if not
            # installed yet) rather than the constructor's placeholder default.
            self.model = explicit_model or saved_model or ""
            return "no-models"

        installed_names = {self.format_model_display_info(m)[0] for m in models}

        def first_available() -> str:
            models.sort(key=lambda m: self.format_model_display_info(m)[0])
            name, _, _ = self.format_model_display_info(models[0])
            return name

        if explicit_model:
            if explicit_model in installed_names:
                self.model = explicit_model
                return None
            self.model = saved_model if saved_model in installed_names else first_available()
            return (explicit_model, self.model)

        if saved_model:
            if saved_model in installed_names:
                self.model = saved_model
                return None
            self.model = first_available()
            return (saved_model, self.model)

        self.model = first_available()
        return "auto-selected"

    def print_resolution_status(self, status: Optional[Any]) -> None:
        """Print the outcome of resolve_initial_model(), if any.

        Args:
            status: The value returned by resolve_initial_model().
        """
        if status is None:
            return
        if status == "no-models":
            self.console.print(Panel(
                "[bold yellow]No Ollama models found on this host.[/bold yellow]\n\n"
                "Pull one in another terminal, for example:\n"
                "[bold cyan]ollama pull qwen3:0.6b[/bold cyan]\n\n"
                "Then restart ollmcp, or run [bold cyan]/model[/bold cyan] once a model is available.",
                title="No Models Available", border_style="yellow", expand=False
            ))
            self.console.print()
        elif status == "auto-selected":
            self.console.print(Panel(
                f"No saved model preference found — using [bold green]{self.model}[/bold green] (first available model).\n\n"
                "• Switch models: [bold cyan]/model[/bold cyan] or [bold cyan]/m[/bold cyan]\n"
                "• Save this as your default: [bold cyan]/save-config[/bold cyan] or [bold cyan]/sc[/bold cyan]",
                title="Model Auto-Selected", border_style="cyan", expand=False
            ))
            self.console.print()
        else:
            requested, used = status
            self.console.print(Panel(
                f"Requested model [bold yellow]{requested}[/bold yellow] is not available — "
                f"using [bold green]{used}[/bold green] instead.\n\n"
                f"Pull it with [bold cyan]ollama pull {requested}[/bold cyan] to use it, or:\n"
                "• Switch models: [bold cyan]/model[/bold cyan] or [bold cyan]/m[/bold cyan]\n"
                "• Save this as your default: [bold cyan]/save-config[/bold cyan] or [bold cyan]/sc[/bold cyan]",
                title="Requested Model Unavailable", border_style="yellow", expand=False
            ))
            self.console.print()
