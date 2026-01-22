"""
Input utilities for the MCP client for Ollama.

This module provides functions for getting user input without autocomplete.
"""
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from .constants import DEFAULT_COMPLETION_STYLE


async def get_input_no_autocomplete(prompt_text: str) -> str:
    """Get user input without autocomplete (for file paths, config names, etc.)

    This is useful for inputs where prompt/command autocomplete would be distracting
    or inappropriate, such as file paths, config names, or prompt arguments.

    Args:
        prompt_text: The prompt text to display (without the ❯ symbol)

    Returns:
        str: User input or 'quit' if cancelled
    """
    try:
        # Create a temporary session without completer
        temp_session = PromptSession(
            style=Style.from_dict(DEFAULT_COMPLETION_STYLE)
        )
        user_input = await temp_session.prompt_async(
            f"{prompt_text}❯ "
        )
        return user_input
    except KeyboardInterrupt:
        return "quit"
    except EOFError:
        return "quit"
