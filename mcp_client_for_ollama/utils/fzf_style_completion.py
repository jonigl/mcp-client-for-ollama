""" FZF-style command completer for interactive mode using prompt_toolkit """
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
from .constants import INTERACTIVE_COMMANDS

class FZFStyleCompleter(Completer):
    """Simple FZF-style completer with fuzzy matching."""

    def __init__(self):
        # Just wrap a WordCompleter with FuzzyCompleter
        self.completer = FuzzyCompleter(WordCompleter(
            list(INTERACTIVE_COMMANDS.keys()),
            ignore_case=True
        ))

    def get_completions(self, document, complete_event):
        # Only complete if cursor is in the first word (commands only)
        text_before_cursor = document.text_before_cursor
        if " " in text_before_cursor:
          return
        # Get fuzzy completions
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
