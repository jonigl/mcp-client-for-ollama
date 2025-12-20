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
        self.num_ctx = None                # int
        self.num_batch =  None             # int
        self.logprobs = None               # bool
        self.top_logprobs = None           # int (0-20)

        # Parameter explanations
        self.parameter_explanations = {
            "system_prompt": {
                "description": "A string placed in the context before any user input to define behavior, style, or persona.",
                "range": "Any UTF-8 string; practical length ≲ 2 kB",
                "effect": "Sets the foundation for how the model behaves throughout the conversation.",
                "recommendation": "Be concise but specific about the desired role, tone, and constraints."
            },
            "num_keep": {
                "description": "Locks the first n tokens of the current context when the window overflows, so they are never discarded.",
                "range": "0 – context size (e.g., 0 – 8192); 0 = no lock",
                "effect": "Does not carry over between separate API calls. Helps retain important context.",
                "recommendation": "Use to keep instruction preamble in context during long conversations."
            },
            "seed": {
                "description": "Integer that initializes the random number generator, making outputs reproducible.",
                "range": "0 – 2³² - 1; -1 picks a random seed",
                "effect": "Same seed + same prompt = same output, enabling deterministic generation.",
                "recommendation": "Set a specific value when reproducibility is needed; leave unset or -1 for varied responses."
            },
            "num_predict": {
                "description": "Maximum number of tokens the model may generate.",
                "range": "0 – context size; 0 lets the server choose",
                "effect": "Limits response length regardless of natural stopping point.",
                "recommendation": "Use higher values for detailed responses, lower for concise answers."
            },
            "top_k": {
                "description": "At each step, sampling is limited to the k most-likely tokens.",
                "range": "0 – vocab size (~50k); 0 disables the filter",
                "effect": "Reduces randomness by excluding unlikely tokens from consideration.",
                "recommendation": "20-40 for balanced output; 0 to disable and rely on other sampling methods."
            },
            "top_p": {
                "description": "Chooses from the smallest set of tokens whose cumulative probability ≥ top_p (nucleus sampling).",
                "range": "0.0 – 1.0",
                "effect": "Controls diversity by only considering tokens above a probability threshold.",
                "recommendation": "0.7-0.9 for natural language; lower for more deterministic responses."
            },
            "min_p": {
                "description": "Filters out tokens whose probability is below min_p × max_prob for that step.",
                "range": "0.0 – 1.0; 0 disables",
                "effect": "Removes very unlikely tokens even if they would be included by top_k/top_p.",
                "recommendation": "0.05-0.1 to filter unlikely tokens while maintaining diversity."
            },
            "typical_p": {
                "description": "Keeps tokens whose conditional probability is near the typical value for the distribution.",
                "range": "0.0 – 1.0; 1 disables",
                "effect": "Applied after top_k and before top_p. Helps generate more natural text.",
                "recommendation": "0.3-0.8 for natural language; 1.0 to disable."
            },
            "repeat_last_n": {
                "description": "Number of recent tokens considered when applying repetition penalties.",
                "range": "-1 (entire context), 0 (disable), or 1 – context size",
                "effect": "Controls how much history is considered when preventing repetition.",
                "recommendation": "64-256 for most applications; -1 for maximum repetition control."
            },
            "temperature": {
                "description": "Scales the logits to control randomness: lower = deterministic, higher = creative.",
                "range": "≥ 0.0; common 0.2 – 1.2",
                "effect": "Higher values make distribution more uniform; lower values make it more peaked.",
                "recommendation": "0.7-0.8 for balanced responses; near 0 for factual/consistent outputs."
            },
            "repeat_penalty": {
                "description": "Multiplies the probability of already-seen tokens by 1 / penalty.",
                "range": "1.0 – 2.0+; 1.0 = off",
                "effect": "Higher values more strongly discourage the model from repeating itself.",
                "recommendation": "1.1-1.3 for subtle repetition control without harming fluency."
            },
            "presence_penalty": {
                "description": "Adds a penalty once a token has appeared, encouraging new topics.",
                "range": "0.0 – 2.0; 0 = off",
                "effect": "Penalizes tokens that have appeared at all, regardless of frequency.",
                "recommendation": "0.1-0.4 for encouraging topic diversity without affecting coherence."
            },
            "frequency_penalty": {
                "description": "Penalizes tokens proportionally to how often they have appeared, reducing repetition.",
                "range": "0.0 – 2.0; 0 = off",
                "effect": "Higher values more strongly discourage frequently used tokens.",
                "recommendation": "0.1-0.4 for reducing word repetition while maintaining coherence."
            },
            "stop": {
                "description": "List of strings; generation halts immediately after any is produced.",
                "range": "0–8 strings, each ≤ 255 characters",
                "effect": "Provides precise control over where generation ends.",
                "recommendation": "Use for controlling dialog format or preventing the model from continuing beyond desired points."
            },
            "num_ctx": {
                "description": "Sets the size of the context window used to generate the next token.",
                "range": "1 – model maximum (e.g., 1 – 32768 for qwen3:0.6b); model-dependent",
                "effect": "Controls how much conversation history and context the model can access when generating responses.",
                "recommendation": "Use higher values for complex conversations requiring more context; balance with memory usage and performance."
            },
            "num_batch":{
                "description":"Sets the batch size for which the prompt request will be divided into during processing.",
                "range":"1 - context size (1 = no batching), default for ollama == 512",
                "effect":"Directly impacts processing speed and response time. Increasing the batch size increases throughput(tokens/sec) upto a point of saturation upon which it starts to deteriorate.",
                "recommendation":"Vary the batch size while observing the performance and memory, choose the best size for your usecase"
            },
            "logprobs": {
                "description": "Returns log probabilities for each generated token, showing the model's confidence (higher logprob = more confident).",
                "range": "true or false",
                "effect": "When enabled, includes token-level log probability information in the response for analysis and debugging.",
                "recommendation": "Enable for debugging and understanding model behavior."
            },
            "top_logprobs": {
                "description": "Number of top alternative tokens and their log probabilities to return for each position.",
                "range": "0 – 20; requires logprobs=true",
                "effect": "Shows alternative token choices the model considered, revealing decision boundaries.",
                "recommendation": "Use 3-5 for reasonable detail; higher values provide more alternatives but increase response size."
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
            "stop": self.stop,
            "num_ctx": self.num_ctx,
            "num_batch": self.num_batch,
            "logprobs": self.logprobs,
            "top_logprobs": self.top_logprobs
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
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        if self.num_batch is not None:
            options["num_batch"] = self.num_batch
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
        if "num_ctx" in config:
            self.num_ctx = config["num_ctx"]
        if "num_batch" in config:
            self.num_batch = config["num_batch"]
        if "logprobs" in config:
            self.logprobs = config["logprobs"]
        if "top_logprobs" in config:
            self.top_logprobs = config["top_logprobs"]

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
            expand=False))

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
            f"[bold][orange3]13.[/orange3] stop:[/bold] {format_value(self.stop)}\n"
            f"[bold][orange3]14.[/orange3] num_ctx:[/bold] {format_value(self.num_ctx)}\n"
            f"[bold][orange3]15.[/orange3] num_batch:[/bold] {format_value(self.num_batch)}\n"
            f"[bold][orange3]16.[/orange3] logprobs:[/bold] {format_value(self.logprobs)}\n"
            f"[bold][orange3]17.[/orange3] top_logprobs:[/bold] {format_value(self.top_logprobs)}",
            title="[bold blue]🎮 Model Parameters[/bold blue]",
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
            "presence_penalty", "frequency_penalty", "stop", "num_ctx","num_batch"
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

            self.console.print(Panel(Text.from_markup("[bold]🪛 Model Configuration[/bold]", justify="center"), expand=True, border_style="green"))
            self.display_current_config()

            if result_message:
                self.console.print(Panel(result_message, border_style=result_style, expand=False))
                result_message = None

            # Show the command panel
            self.console.print(Panel("[bold yellow]Commands[/bold yellow]", expand=False))
            self.console.print("Enter [bold magenta]sp[/bold magenta] or [bold magenta]system_prompt[/bold magenta] - [bold]Set the system prompt[/bold] [dim](e.g., You are a helpful assistant.)[/dim]")
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
                self.num_ctx = None
                self.num_batch = None
                self.logprobs = None
                self.top_logprobs = None
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
                        case 14:
                            self.num_ctx = None
                            result_message = "[green]num_ctx unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 15:
                            self.num_batch = None
                            result_message = "[green]num_batch unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 16:
                            self.logprobs = None
                            result_message = "[green]logprobs unset (using Ollama default).[/green]"
                            result_style = "green"
                        case 17:
                            self.top_logprobs = None
                            result_message = "[green]top_logprobs unset (using Ollama default).[/green]"
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
                    prompt_text = f"System Prompt (string to define behavior, style, or persona) [{current}]:"
                    new_value = Prompt.ask(prompt_text, default=self.system_prompt)
                    if new_value or not current:
                        self.system_prompt = new_value
                        result_message = "[green]System prompt updated.[/green]"
                        result_style = "green"

                case "1":
                    try:
                        new_value = IntPrompt.ask("Keep Tokens (num_keep, 0 to context size)", default=self.num_keep)
                        if new_value >= 0:
                            self.num_keep = new_value
                            result_message = f"[green]num_keep set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]num_keep must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "2":
                    try:
                        new_value = IntPrompt.ask("Seed (integer for reproducible outputs, -1 for random)", default=self.seed)
                        if new_value >= -1:
                            self.seed = new_value
                            result_message = f"[green]seed set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]seed must be -1 or a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "3":
                    try:
                        new_value = IntPrompt.ask("Max Tokens (num_predict, 0 to context size; 0 lets the server choose)", default=self.num_predict)
                        if new_value >= 0:
                            self.num_predict = new_value
                            result_message = f"[green]num_predict set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]num_predict must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "4":
                    try:
                        new_value = IntPrompt.ask("Top K (0 to disable)", default=self.top_k)
                        if new_value >= 0:
                            self.top_k = new_value
                            result_message = f"[green]top_k set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]top_k must be a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "5":
                    try:
                        new_value = FloatPrompt.ask("Top P (0.0-1.0)", default=self.top_p)
                        if 0.0 <= new_value <= 1.0:
                            self.top_p = new_value
                            result_message = f"[green]top_p set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]top_p must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "6":
                    try:
                        new_value = FloatPrompt.ask("Min P (0.0-1.0, 0 disables)", default=self.min_p)
                        if 0.0 <= new_value <= 1.0:
                            self.min_p = new_value
                            result_message = f"[green]min_p set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]min_p must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "7":
                    try:
                        new_value = FloatPrompt.ask("Typical P (0.0-1.0, 1.0 disables)", default=self.typical_p)
                        if 0.0 <= new_value <= 1.0:
                            self.typical_p = new_value
                            result_message = f"[green]typical_p set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]typical_p must be between 0.0 and 1.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "8":
                    try:
                        new_value = IntPrompt.ask("Repeat Last N (-1 for entire context, 0 to disable)", default=self.repeat_last_n)
                        if new_value >= -1:
                            self.repeat_last_n = new_value
                            result_message = f"[green]repeat_last_n set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]repeat_last_n must be -1 or a non-negative integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "9":
                    try:
                        new_value = FloatPrompt.ask("Temperature (≥ 0.0, lower = deterministic, higher = creative)", default=self.temperature)
                        if new_value >= 0.0:
                            self.temperature = new_value
                            result_message = f"[green]temperature set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]temperature must be non-negative.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "10":
                    try:
                        new_value = FloatPrompt.ask("Repeat Penalty (≥ 1.0, 1.0 = no penalty)", default=self.repeat_penalty)
                        if new_value >= 1.0:
                            self.repeat_penalty = new_value
                            result_message = f"[green]repeat_penalty set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]repeat_penalty must be 1.0 or higher.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "11":
                    try:
                        new_value = FloatPrompt.ask("Presence Penalty (0.0-2.0, 0 = no penalty)", default=self.presence_penalty)
                        if 0.0 <= new_value <= 2.0:
                            self.presence_penalty = new_value
                            result_message = f"[green]presence_penalty set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]presence_penalty must be between 0.0 and 2.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "12":
                    try:
                        new_value = FloatPrompt.ask("Frequency Penalty (0.0-2.0, 0 = no penalty)", default=self.frequency_penalty)
                        if 0.0 <= new_value <= 2.0:
                            self.frequency_penalty = new_value
                            result_message = f"[green]frequency_penalty set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]frequency_penalty must be between 0.0 and 2.0.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid number.[/red]"
                        result_style = "red"

                case "13":
                    default_val = ",".join(self.stop) if self.stop is not None else None
                    new_value = Prompt.ask("Stop Sequences (comma-separated)", default=default_val)
                    if new_value and new_value.strip():
                        sequences = [seq.strip() for seq in new_value.split(",") if seq.strip()]
                        if len(sequences) <= 8 and all(len(seq) <= 255 for seq in sequences):
                            self.stop = sequences
                            result_message = f"[green]stop sequences set to {self.stop}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]Maximum 8 sequences, each ≤ 255 characters.[/red]"
                            result_style = "red"
                    else:
                        self.stop = []
                        result_message = "[green]stop sequences cleared.[/green]"
                        result_style = "green"

                case "14":
                    try:
                        new_value = IntPrompt.ask("Context Size (num_ctx, size of context window)", default=self.num_ctx)
                        if new_value >= 1:
                            self.num_ctx = new_value
                            result_message = f"[green]num_ctx set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]num_ctx must be a positive integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"
                case "15":
                    try:
                        new_value = IntPrompt.ask("Batch Size (num_batch, size of batches by which prompt is divided)", default=self.num_batch)
                        if new_value >= 1:
                            self.num_batch = new_value
                            result_message = f"[green]num_batch set to {new_value}.[/green]"
                            result_style = "green"
                        else:
                            result_message = "[red]num_batch must be a positive integer.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case "16":
                    current_val = "true" if self.logprobs else "false" if self.logprobs is False else "true"
                    new_value = Prompt.ask("Enable Log Probabilities (true/false)", default=current_val)
                    if new_value and new_value.lower() in ['true', 't', 'yes', 'y', '1']:
                        self.logprobs = True
                        result_message = "[green]logprobs enabled.[/green]"
                        result_style = "green"
                    elif new_value and new_value.lower() in ['false', 'f', 'no', 'n', '0']:
                        self.logprobs = False
                        result_message = "[green]logprobs disabled.[/green]"
                        result_style = "green"
                    else:
                        result_message = "[red]Please enter true or false.[/red]"
                        result_style = "red"

                case "17":
                    try:
                        new_value = IntPrompt.ask("Top Log Probabilities (0-20, number of alternative tokens to show)", default=self.top_logprobs)
                        if 0 <= new_value <= 20:
                            self.top_logprobs = new_value
                            result_message = f"[green]top_logprobs set to {new_value}.[/green]"
                            result_style = "green"
                            if self.logprobs is not True:
                                result_message += "\n[yellow]Note: logprobs must be enabled (option 16) for this to take effect.[/yellow]"
                        else:
                            result_message = "[red]top_logprobs must be between 0 and 20.[/red]"
                            result_style = "red"
                    except ValueError:
                        result_message = "[red]Please enter a valid integer.[/red]"
                        result_style = "red"

                case _:
                    result_message = "[red]Invalid selection. Please choose a valid option.[/red]"
                    result_style = "red"
