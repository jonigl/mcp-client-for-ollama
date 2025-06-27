"""Model configuration management for MCP Client for Ollama.

This module handles model configuration options like system prompt, temperature, and top_k.
"""
from typing import Dict, Any, Optional, Callable
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich.text import Text
from rich.table import Table
import rich.box

class ModelConfigManager:
    """Manages model configuration options.

    This class handles configuration of system prompts and model parameters
    like temperature, top_k, etc. Only sends configured options to Ollama,
    allowing Ollama to use its own defaults for unset values.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the ModelConfigManager.

        Args:
            console: Rich console for output (optional)
        """
        self.console = console or Console()
        self.system_prompt = ""
        # All options start as None (unset) to rely on Ollama's defaults
        self.num_keep = None               # int
        self.seed = None                   # int
        self.num_predict = None            # int
        self.top_k = None                  # int
        self.top_p = None                  # float
        self.min_p = None                  # float
        self.typical_p = None              # float
        self.repeat_last_n = None          # int
        self.temperature = None            # float
        self.repeat_penalty = None         # float
        self.presence_penalty = None       # float
        self.frequency_penalty = None      # float
        self.stop = None                   # list[str]

        # Parameter explanations
        self.parameter_explanations = {
            "system_prompt": {
                "description": "Provides context and instructions to guide the model's behavior.",
                "range": "Free-form text",
                "effect": "Sets the style, tone, and capabilities of the model's responses.",
                "recommendation": "Be clear and specific about the role and constraints you want the model to follow."
            },
            "num_keep": {
                "description": "Number of tokens to keep from the prompt when the context window overflows.",
                "range": "0 to model context size (e.g., 0-8192)",
                "effect": "Controls how much prompt context is preserved during long conversations.",
                "recommendation": "Higher values preserve more context but use more tokens."
            },
            "seed": {
                "description": "Random seed to use for generation.",
                "range": "Any integer (e.g., 1-4294967295), or 0 for random",
                "effect": "Controls reproducibility of outputs. Same seed = same output for same prompt.",
                "recommendation": "Set to 0 for non-deterministic outputs, or use a specific value for reproducible responses."
            },
            "num_predict": {
                "description": "Maximum number of tokens to generate in the response.",
                "range": "1 to model maximum (typically 128-2048)",
                "effect": "Limits the length of the generated text.",
                "recommendation": "Lower values for short answers, higher for detailed responses."
            },
            "top_k": {
                "description": "Limits token selection to the K most likely tokens at each step.",
                "range": "0 (disabled) to 100+",
                "effect": "Lower values increase focus and determinism, higher values increase diversity.",
                "recommendation": "0 to disable, 10-40 for balanced generation."
            },
            "top_p": {
                "description": "Limits token selection to tokens comprising the top_p probability mass.",
                "range": "0.0 to 1.0",
                "effect": "Lower values increase focus on most likely tokens, higher values include more diverse options.",
                "recommendation": "0.7-0.9 for balanced generation."
            },
            "min_p": {
                "description": "Filters tokens below this probability threshold relative to the most likely token.",
                "range": "0.0 to 1.0",
                "effect": "Eliminates unlikely tokens from consideration.",
                "recommendation": "0.05-0.1 to remove unlikely tokens while maintaining diversity."
            },
            "typical_p": {
                "description": "Selects tokens based on how typical they are relative to expected entropy.",
                "range": "0.0 to 1.0",
                "effect": "Controls selection of tokens based on their typicality rather than raw probability.",
                "recommendation": "0.3-0.8 for more natural-sounding text."
            },
            "repeat_last_n": {
                "description": "Number of previous tokens to consider for the repeat penalty calculation.",
                "range": "0 to model context size (0 = disabled)",
                "effect": "Controls how much context is considered when penalizing repetitions.",
                "recommendation": "64-256 for balanced repetition control."
            },
            "temperature": {
                "description": "Controls randomness of token selection.",
                "range": "0.0 to 2.0+",
                "effect": "0.0 = deterministic (always pick most likely), 1.0+ = increasingly random selection.",
                "recommendation": "0.7-0.8 for balanced creativity, 0.0-0.3 for factual/logical responses."
            },
            "repeat_penalty": {
                "description": "Penalizes repeating the same tokens.",
                "range": "1.0 (no penalty) to 2.0+",
                "effect": "Higher values reduce repetition more aggressively.",
                "recommendation": "1.1-1.3 for subtle repetition reduction."
            },
            "presence_penalty": {
                "description": "Penalizes tokens that appear at all, regardless of frequency.",
                "range": "0.0 (no penalty) to 1.0+",
                "effect": "Higher values encourage using new tokens that haven't appeared yet.",
                "recommendation": "0.1-0.4 for balanced generation."
            },
            "frequency_penalty": {
                "description": "Penalizes tokens proportionally to how frequently they've appeared.",
                "range": "0.0 (no penalty) to 1.0+",
                "effect": "Higher values more strongly discourage frequent tokens.",
                "recommendation": "0.1-0.4 for balanced generation."
            },
            "stop": {
                "description": "Sequences that will end generation when produced.",
                "range": "List of strings",
                "effect": "Stops generation when any sequence in the list is generated.",
                "recommendation": "Use for controlling output format or limiting generation."
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """Get the current model configuration.

        Returns:
            Dict containing the model configuration
        """
        return {
            "system_prompt": self.system_prompt,
            "num_keep": self.num_keep,
            "seed": self.seed,
            "num_predict": self.num_predict,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "typical_p": self.typical_p,
            "repeat_last_n": self.repeat_last_n,
            "temperature": self.temperature,
            "repeat_penalty": self.repeat_penalty,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "stop": self.stop
        }

    def get_ollama_options(self) -> Dict[str, Any]:
        """Get model configuration formatted for Ollama API.

        Only includes options that have been explicitly set by the user,
        allowing Ollama to use its own defaults for unset values.

        Returns:
            Dict containing only the configured Ollama-compatible options
        """
        options = {}
        if self.num_keep is not None:
            options["num_keep"] = self.num_keep
        if self.seed is not None:
            options["seed"] = self.seed
        if self.num_predict is not None:
            options["num_predict"] = self.num_predict
        if self.top_k is not None:
            options["top_k"] = self.top_k
        if self.top_p is not None:
            options["top_p"] = self.top_p
        if self.min_p is not None:
            options["min_p"] = self.min_p
        if self.typical_p is not None:
            options["typical_p"] = self.typical_p
        if self.repeat_last_n is not None:
            options["repeat_last_n"] = self.repeat_last_n
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.repeat_penalty is not None:
            options["repeat_penalty"] = self.repeat_penalty
        if self.presence_penalty is not None:
            options["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            options["frequency_penalty"] = self.frequency_penalty
        if self.stop is not None:
            options["stop"] = self.stop
        return options

    def get_system_prompt(self) -> str:
        """Get the current system prompt.

        Returns:
            The system prompt string
        """
        return self.system_prompt

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set model configuration from a dictionary.

        Args:
            config: Dictionary containing model configuration
        """
        if "system_prompt" in config:
            self.system_prompt = config["system_prompt"]
        if "num_keep" in config:
            self.num_keep = config["num_keep"]
        if "seed" in config:
            self.seed = config["seed"]
        if "num_predict" in config:
            self.num_predict = config["num_predict"]
        if "top_k" in config:
            self.top_k = config["top_k"]
        if "top_p" in config:
            self.top_p = config["top_p"]
        if "min_p" in config:
            self.min_p = config["min_p"]
        if "typical_p" in config:
            self.typical_p = config["typical_p"]
        if "repeat_last_n" in config:
            self.repeat_last_n = config["repeat_last_n"]
        if "temperature" in config:
            self.temperature = config["temperature"]
        if "repeat_penalty" in config:
            self.repeat_penalty = config["repeat_penalty"]
        if "presence_penalty" in config:
            self.presence_penalty = config["presence_penalty"]
        if "frequency_penalty" in config:
            self.frequency_penalty = config["frequency_penalty"]
        if "stop" in config:
            self.stop = config["stop"]

    def display_current_config(self) -> None:
        """Display the current model configuration."""
        def format_value(value):
            return str(value) if value is not None else "-"

        # Display system prompt in a separate expandable panel
        system_prompt_text = self.system_prompt if self.system_prompt else "(None)"
        self.console.print(Panel(
            system_prompt_text,
            title="[bold magenta]💬 System Prompt[/bold magenta]",
            border_style="magenta",
            expand=True))

        # Display other model parameters
        self.console.print(Panel(
            f"[bold][orange3]1.[/orange3] num_keep:[/bold] {format_value(self.num_keep)}\n"
            f"[bold][orange3]2.[/orange3] seed:[/bold] {format_value(self.seed)}\n"
            f"[bold][orange3]3.[/orange3] num_predict:[/bold] {format_value(self.num_predict)}\n"
            f"[bold][orange3]4.[/orange3] top_k:[/bold] {format_value(self.top_k)}\n"
            f"[bold][orange3]5.[/orange3] top_p:[/bold] {format_value(self.top_p)}\n"
            f"[bold][orange3]6.[/orange3] min_p:[/bold] {format_value(self.min_p)}\n"
            f"[bold][orange3]7.[/orange3] typical_p:[/bold] {format_value(self.typical_p)}\n"
            f"[bold][orange3]8.[/orange3] repeat_last_n:[/bold] {format_value(self.repeat_last_n)}\n"
            f"[bold][orange3]9.[/orange3] temperature:[/bold] {format_value(self.temperature)}\n"
            f"[bold][orange3]10.[/orange3] repeat_penalty:[/bold] {format_value(self.repeat_penalty)}\n"
            f"[bold][orange3]11.[/orange3] presence_penalty:[/bold] {format_value(self.presence_penalty)}\n"
            f"[bold][orange3]12.[/orange3] frequency_penalty:[/bold] {format_value(self.frequency_penalty)}\n"
            f"[bold][orange3]13.[/orange3] stop:[/bold] {format_value(self.stop)}",
            title="[bold blue]📝 Model Parameters[/bold blue]",
            border_style="blue", expand=False))
        self.console.print("\n[bold yellow]Note:[/bold yellow] Unset values will use Ollama's defaults.")
        self.console.print()

    def display_parameter_explanations(self) -> None:
        """Display detailed explanations for all model parameters in a scrollable format.

        Shows consolidated, easy-to-read information about each parameter's purpose,
        range, effect, and recommended usage.
        """
        # Create a renderable group that will contain all our content
        content = []

        # Create header
        header = Panel(
            Text.from_markup("[bold]🔎 Model Parameter Reference Guide[/bold]", justify="center"),
            expand=True,
            border_style="green"
        )
        content.append(header)

        # Create a table for the parameters
        table = Table(
            show_header=True,
            header_style="bold yellow",
            show_lines=True,
            expand=True,
            box=rich.box.ROUNDED
        )

        # Add columns
        table.add_column("Parameter", style="cyan", width=16)
        table.add_column("Description", width=40)
        table.add_column("Range", width=20)
        table.add_column("Recommendation", width=30)

        # Special styling for the system prompt
        param = "system_prompt"
        info = self.parameter_explanations[param]
        table.add_row(
            f"[bold magenta]💬 {param}[/bold magenta]",
            f"{info['description']}\n[dim]{info['effect']}[/dim]",
            info['range'],
            info['recommendation']
        )

        # Add all other parameters
        for param in [
            "num_keep", "seed", "num_predict", "top_k", "top_p", "min_p",
            "typical_p", "repeat_last_n", "temperature", "repeat_penalty",
            "presence_penalty", "frequency_penalty", "stop"
        ]:
            info = self.parameter_explanations[param]
            table.add_row(
                f"[bold blue]{param}[/bold blue]",
                f"{info['description']}\n[dim]{info['effect']}[/dim]",
                info['range'],
                info['recommendation']
            )

        content.append(table)

        # Add a section for common parameter combinations
        content.append("")
        content.append("[bold]📋 Common Parameter Combinations[/bold]")

        combinations_table = Table(show_header=True, header_style="bold yellow", expand=True)
        combinations_table.add_column("Use Case", style="cyan")
        combinations_table.add_column("Recommended Settings")

        combinations_table.add_row(
            "Factual, deterministic responses",
            "temperature=0.0-0.3, top_p=0.1-0.5"
        )
        combinations_table.add_row(
            "Balanced, natural responses",
            "temperature=0.7, top_p=0.9, typical_p=0.7"
        )
        combinations_table.add_row(
            "Creative, varied responses",
            "temperature=1.0+, top_p=0.95, presence_penalty=0.2"
        )
        combinations_table.add_row(
            "Reduce repetition",
            "repeat_penalty=1.2, presence_penalty=0.2, frequency_penalty=0.3"
        )
        combinations_table.add_row(
            "Reproducible outputs",
            "seed=42 (or any fixed integer value)"
        )

        content.append(combinations_table)
        content.append("\n[bold yellow]Press Q to exit the parameter guide.[/bold yellow]")

        # Create a Group of all the rendered content
        group = Group(*content)

        # Use the console's pager to display the content
        # to provide a scrollable interface with keyboard navigation
        with self.console.pager(styles=True):
            self.console.print(group)

    def configure_model_interactive(self, clear_console_func: Optional[Callable] = None) -> None:
        """Interactively configure model parameters."""
        original_config = self.get_config()
        result_message = None
        result_style = "red"

        while True:
            if clear_console_func:
                clear_console_func()

            self.console.print(Panel(Text.from_markup("[bold]🎛️  Model Configuration[/bold]", justify="center"), expand=True, border_style="green"))
            self.display_current_config()

            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None

            # Show the command panel
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print("Enter [bold magenta]sp[/bold magenta] or [bold magenta]system_prompt[/bold magenta] - [bold]Set the system prompt[/bold]")
            self.console.print("Enter [bold orange3]number[/bold orange3] - [bold]Set a parameter[/bold] [dim](e.g., 1 for num_keep, 9 for temperature)[/dim]")
            self.console.print("Enter [bold][orange3]u[/orange3] + [orange3]number[/orange3][/bold] or [bold][magenta]usp[/magenta][/bold] - [bold]Unset a parameter[/bold] [dim](e.g., u1 to unset num_keep, usp to unset system_prompt)[/dim]")
            self.console.print("[bold]uall[/bold] - Unset all parameters [dim](use Ollama defaults)[/dim]")
            self.console.print("[bold]undo[/bold] - Restore original settings [dim](from before changes)[/dim]")
            self.console.print("[bold]h[/bold] or [bold]help[/bold] - Show Parameter Reference Guide")
            self.console.print("[bold]s[/bold] or [bold]save[/bold] - Save changes and return")
            self.console.print("[bold]q[/bold] or [bold]quit[/bold] - Cancel changes and return")

            selection = Prompt.ask("> ")
            selection = selection.strip().lower()

            if selection in ['s', 'save']:
                if clear_console_func:
                    clear_console_func()
                return

            if selection in ['q', 'quit']:
                self.set_config(original_config)
                if clear_console_func:
                    clear_console_func()
                return

            if selection == 'undo':
                self.set_config(original_config)
                result_message = "[green]Settings restored to original values.[/green]"
                result_style = "green"
                continue

            if selection in ['h', 'help']:
                if clear_console_func:
                    clear_console_func()
                self.display_parameter_explanations()
                continue

            if selection == 'uall':
                self.system_prompt = ""
                self.num_keep = None
                self.seed = None
                self.num_predict = None
                self.top_k = None
                self.top_p = None
                self.min_p = None
                self.typical_p = None
                self.repeat_last_n = None
                self.temperature = None
                self.repeat_penalty = None
                self.presence_penalty = None
                self.frequency_penalty = None
                self.stop = None
                result_message = "[green]All parameters unset (using Ollama defaults).[/green]"
                result_style = "green"
                continue

            # Handle shorthand unset commands (e.g., u1, usp)
            if selection.startswith('u') and len(selection) > 1:
                param_to_unset = selection[1:]  # Extract the part after 'u'

                # Handle parameter unset by shorthand (u + number or usp)
                if param_to_unset == "sp" or param_to_unset == "system_prompt":
                    self.system_prompt = ""
                    result_message = "[green]system_prompt unset (using Ollama default).[/green]"
                    result_style = "green"
                    continue

                # Try to convert to integer for numbered parameters
                try:
                    param_num = int(param_to_unset)
                    # Map parameter numbers to their actions
                    match param_num:
                        case 1:
                            self.num_keep = None
                            result_message = "[green]num_keep unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 2:
                            self.seed = None
                            result_message = "[green]seed unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 3:
                            self.num_predict = None
                            result_message = "[green]num_predict unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 4:
                            self.top_k = None
                            result_message = "[green]top_k unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 5:
                            self.top_p = None
                            result_message = "[green]top_p unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 6:
                            self.min_p = None
                            result_message = "[green]min_p unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 7:
                            self.typical_p = None
                            result_message = "[green]typical_p unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 8:
                            self.repeat_last_n = None
                            result_message = "[green]repeat_last_n unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 9:
                            self.temperature = None
                            result_message = "[green]temperature unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 10:
                            self.repeat_penalty = None
                            result_message = "[green]repeat_penalty unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 11:
                            self.presence_penalty = None
                            result_message = "[green]presence_penalty unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 12:
                            self.frequency_penalty = None
                            result_message = "[green]frequency_penalty unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 13:
                            self.stop = None
                            result_message = "[green]stop unset (using Ollama default).[/green]"
                            result_style = "green"
                        case _:
                            result_message = "[red]Invalid parameter number.[/red]"
                            result_style = "red"
                except ValueError:
                    result_message = f"[red]Invalid unset command: {selection}[/red]"
                    result_style = "red"

                continue

            match selection:
                case "sp" | "system_prompt":
                    current = self.system_prompt
                    prompt_text = f"System Prompt (empty to keep current: '{current}')" if current else "System Prompt"
                    new_value = Prompt.ask(prompt_text, default="")
                    if new_value or not current:
                        self.system_prompt = new_value
                        result_message = "[green]System prompt updated.[/green]"
                        result_style = "green"

                case "1":
                    try:
                        new_value = IntPrompt.ask("Keep Tokens (num_keep)", default=self.num_keep)
                        if new_value >= 0:
                            self.num_keep = new_value
                            result_message = f"[green]Keep Tokens set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Keep Tokens must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "2":
                    try:
                        new_value = IntPrompt.ask("Seed (integer for reproducible outputs)", default=self.seed)
                        self.seed = new_value
                        result_message = f"[green]Seed set to {new_value}.[/green]"
                        result_style = "green"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "3":
                    try:
                        new_value = IntPrompt.ask("Max Tokens (num_predict)", default=self.num_predict)
                        if new_value > 0:
                            self.num_predict = new_value
                            result_message = f"[green]Max Tokens set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Max Tokens must be a positive integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "4":
                    try:
                        new_value = IntPrompt.ask("Top K (0 to disable)", default=self.top_k)
                        if new_value >= 0:
                            self.top_k = new_value
                            result_message = f"[green]Top K set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Top K must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "5":
                    try:
                        new_value = FloatPrompt.ask("Top P (0.0-1.0)", default=self.top_p)
                        if 0.0 <= new_value <= 1.0:
                            self.top_p = new_value
                            result_message = f"[green]Top P set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Top P must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "6":
                    try:
                        new_value = FloatPrompt.ask("Min P (0.0-1.0)", default=self.min_p)
                        if 0.0 <= new_value <= 1.0:
                            self.min_p = new_value
                            result_message = f"[green]Min P set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Min P must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "7":
                    try:
                        new_value = FloatPrompt.ask("Typical P (0.0-1.0)", default=self.typical_p)
                        if 0.0 <= new_value <= 1.0:
                            self.typical_p = new_value
                            result_message = f"[green]Typical P set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Typical P must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "8":
                    try:
                        new_value = IntPrompt.ask("Repeat Last N (context for repetition penalty)", default=self.repeat_last_n)
                        if new_value >= 0:
                            self.repeat_last_n = new_value
                            result_message = f"[green]Repeat Last N set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Repeat Last N must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "9":
                    try:
                        new_value = FloatPrompt.ask("Temperature (0.0 = deterministic, 1.0+ = creative)", default=self.temperature)
                        if new_value >= 0.0:
                            self.temperature = new_value
                            result_message = f"[green]Temperature set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Temperature must be non-negative.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "10":
                    try:
                        new_value = FloatPrompt.ask("Repeat Penalty (1.0 = no penalty)", default=self.repeat_penalty)
                        if new_value >= 0.0:
                            self.repeat_penalty = new_value
                            result_message = f"[green]Repeat Penalty set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Repeat Penalty must be non-negative.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "11":
                    try:
                        new_value = FloatPrompt.ask("Presence Penalty (0.0 = no penalty)", default=self.presence_penalty)
                        self.presence_penalty = new_value
                        result_message = f"[green]Presence Penalty set to {new_value}.[/green]"
                        result_style = "green"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "12":
                    try:
                        new_value = FloatPrompt.ask("Frequency Penalty (0.0 = no penalty)", default=self.frequency_penalty)
                        self.frequency_penalty = new_value
                        result_message = f"[green]Frequency Penalty set to {new_value}.[/green]"
                        result_style = "green"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "13":
                    default_val = ",".join(self.stop) if self.stop is not None else None
                    new_value = Prompt.ask("Stop Sequences (comma-separated)", default=default_val)
                    if new_value and new_value.strip():
                        self.stop = [seq.strip() for seq in new_value.split(",") if seq.strip()]
                        result_message = f"[green]Stop Sequences set to {self.stop}.[/green]"
                        result_style = "green"
                    else:
                        self.stop = []
                        result_message = "[green]Stop Sequences cleared.[/green]"
                        result_style = "green"

                case _:
                    result_message = "[red]Invalid selection. Please choose a valid option.[/red]"
                    result_style = "red"
