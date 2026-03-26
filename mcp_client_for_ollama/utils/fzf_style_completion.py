""" FZF-style command completer for interactive mode using prompt_toolkit """
import shutil
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from .constants import INTERACTIVE_COMMANDS


class FZFStyleCompleter(Completer):
    """Simple FZF-style completer with fuzzy matching."""

    def __init__(self):
        # Wrap command names with FuzzyCompleter for slash command completion.
        self.command_completer = FuzzyCompleter(WordCompleter(
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

    def _build_action_meta(self, action_type: str, description: str) -> FormattedText:
        """Build action badge metadata for completion rows."""
        return FormattedText([
            ("bg:#ff8c00 #111111 bold", action_type.upper()),
            ("bg:#1e1e1e #d6d6d6", f" {description}" if description else "")
        ])

    def _get_prompt_completions(self, prompt_query):
        """Generate qualified prompt completions for slash namespace.

        Args:
            prompt_query: The token being typed after /

        Yields:
            Completion objects for matching prompts
        """
        # If no prompts available, show a helpful message
        if not self.prompts:
            return

        # Filter and rank prompts by matching
        matches = []
        for prompt in self.prompts:
            name = prompt['name']
            server_name = prompt.get('server', '')
            qualified_name = prompt.get('qualified_name') or f"{server_name}:{name}"
            description = prompt.get('description', '')

            # Simple fuzzy matching
            if (
                prompt_query in qualified_name.lower()
                or prompt_query in name.lower()
                or prompt_query in server_name.lower()
                or (description and prompt_query in description.lower())
            ):
                matches.append(prompt)

        # Return prompt completions
        for prompt in matches:
            name = prompt['name']
            server_name = prompt.get('server', '')
            qualified_name = prompt.get('qualified_name') or f"{server_name}:{name}"
            display_meta = prompt.get('description', '') or ''

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

            display = f"/{qualified_name}"

            # Start position should replace the / and what comes after
            yield Completion(
                qualified_name,
                start_position=-len(prompt_query),
                display=display,
                display_meta=self._build_action_meta("prompt", display_meta)
            )

    def _get_slash_command_completions(self, prompt_query, complete_event):
        """Generate slash command completions for /command syntax.

        Args:
            prompt_query: The token being typed after /
            complete_event: The completion event

        Yields:
            Completion objects for matching commands
        """
        query_document = Document(text=prompt_query, cursor_position=len(prompt_query))
        for completion in self.command_completer.get_completions(query_document, complete_event):
            cmd = completion.text
            description = INTERACTIVE_COMMANDS.get(cmd, "")

            yield Completion(
                cmd,
                start_position=completion.start_position,
                display=f"/{cmd}",
                display_meta=self._build_action_meta("command", description)
            )

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        # Slash namespace combines built-in commands and prompts.
        if text_before_cursor.startswith('/'):
            prompt_query = text_before_cursor[1:].lower()
            yielded_any = False

            for completion in self._get_slash_command_completions(prompt_query, complete_event):
                yielded_any = True
                yield completion

            yield from self._get_prompt_completions(prompt_query)
            if not yielded_any and prompt_query == "":
                return

        # Keep plain query typing free from action autocomplete noise.
        return
