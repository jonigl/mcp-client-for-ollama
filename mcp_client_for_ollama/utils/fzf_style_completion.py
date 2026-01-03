""" FZF-style command completer for interactive mode using prompt_toolkit """
import shutil
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
from .constants import INTERACTIVE_COMMANDS
from ..prompts.display import format_args_indicator


class FZFStyleCompleter(Completer):
    """Simple FZF-style completer with fuzzy matching."""

    def __init__(self):
        # Just wrap a WordCompleter with FuzzyCompleter for commands
        self.completer = FuzzyCompleter(WordCompleter(
            list(INTERACTIVE_COMMANDS.keys()),
            ignore_case=True
        ))
        self.prompts = []  # List of prompt info dicts

    def set_prompts(self, prompts):
        """Set available prompts for completion

        Args:
            prompts: List of prompt info dicts with 'name', 'description', 'arguments'
        """
        self.prompts = prompts

    def _get_prompt_completions(self, prompt_query):
        """Generate completions for prompt invocations (starting with /)

        Args:
            prompt_query: The prompt name being typed (without the /)

        Yields:
            Completion objects for matching prompts
        """
        # Filter and rank prompts by matching
        matches = []
        for prompt in self.prompts:
            name = prompt['name']
            description = prompt.get('description', '')

            # Simple fuzzy matching
            if prompt_query in name.lower() or (description and prompt_query in description.lower()):
                matches.append(prompt)

        # Return prompt completions
        for i, prompt in enumerate(matches[:10]):  # Limit to 10 matches
            name = prompt['name']
            description = prompt.get('description', '') or ''
            arguments = prompt.get('arguments', [])

            # Format args indicator (arguments are PromptArgument objects)
            args_str = format_args_indicator(arguments)

            # Combine description with args
            display_meta = f"{description} {args_str}".strip() if args_str else description

            # Get terminal width and calculate max description length
            # Use 60% of terminal width for description, with min 60 and max 200 chars
            try:
                terminal_width = shutil.get_terminal_size().columns
                # Reserve space for prompt name (estimated ~30 chars) and padding
                available_width = terminal_width - 30
                max_desc_length = max(60, min(200, int(available_width * 0.7)))
            except (AttributeError, ValueError):
                # Fallback if terminal size detection fails
                max_desc_length = 100

            # Truncate long descriptions based on terminal width
            if len(display_meta) > max_desc_length:
                display_meta = display_meta[:max_desc_length - 3] + "..."

            # Add arrow to first match
            display = f"▶ /{name}" if i == 0 else f"  /{name}"

            # Start position should replace the / and what comes after
            yield Completion(
                name,
                start_position=-len(prompt_query),
                display=display,
                display_meta=display_meta
            )

    def _get_command_completions(self, document, complete_event):
        """Generate completions for interactive commands

        Args:
            document: The prompt_toolkit document
            complete_event: The completion event

        Yields:
            Completion objects for matching commands
        """
        for i, completion in enumerate(self.completer.get_completions(document, complete_event)):
            cmd = completion.text
            description = INTERACTIVE_COMMANDS.get(cmd, "")

            # Add arrow to first match
            display = f"▶ {cmd}" if i == 0 else f"  {cmd}"

            yield Completion(
                cmd,
                start_position=completion.start_position,
                display=display,
                display_meta=description
            )

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        # Check if we're triggering prompt completion (starts with /)
        if text_before_cursor.startswith('/'):
            prompt_query = text_before_cursor[1:].lower()
            yield from self._get_prompt_completions(prompt_query)
            return

        # Regular command completion (only if cursor is in first word)
        if " " in text_before_cursor:
            return

        yield from self._get_command_completions(document, complete_event)
