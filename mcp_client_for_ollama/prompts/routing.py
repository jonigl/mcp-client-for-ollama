"""Slash routing utilities for commands and prompt invocations."""

from typing import Optional, Tuple


SLASH_COMMAND_ALIASES = {
    "quit": "quit",
    "q": "quit",
    "exit": "quit",
    "bye": "quit",
    "tools": "tools",
    "t": "tools",
    "help": "help",
    "h": "help",
    "model": "model",
    "m": "model",
    "model-config": "model-config",
    "mc": "model-config",
    "context": "context",
    "c": "context",
    "thinking-mode": "thinking-mode",
    "tm": "thinking-mode",
    "show-thinking": "show-thinking",
    "st": "show-thinking",
    "loop-limit": "loop-limit",
    "ll": "loop-limit",
    "show-tool-execution": "show-tool-execution",
    "ste": "show-tool-execution",
    "show-metrics": "show-metrics",
    "sm": "show-metrics",
    "display-mode": "display-mode",
    "dm": "display-mode",
    "clear": "clear",
    "cc": "clear",
    "context-info": "context-info",
    "ci": "context-info",
    "clear-screen": "clear-screen",
    "cls": "clear-screen",
    "save-config": "save-config",
    "sc": "save-config",
    "load-config": "load-config",
    "lc": "load-config",
    "reset-config": "reset-config",
    "rc": "reset-config",
    "reload-servers": "reload-servers",
    "rs": "reload-servers",
    "human-in-the-loop": "human-in-the-loop",
    "hil": "human-in-the-loop",
    "prompts": "prompts",
    "pr": "prompts",
    "full-history": "full-history",
    "fh": "full-history",
    "export-history": "export-history",
    "eh": "export-history",
    "import-history": "import-history",
    "ih": "import-history",
}


def resolve_slash_command(user_input: str) -> Optional[str]:
    """Resolve command aliases to canonical command names."""
    return SLASH_COMMAND_ALIASES.get(user_input.strip().lower())


def parse_user_input(user_input: str) -> Tuple[str, Optional[str]]:
    """Parse user input into slash command/prompt/query intents.

    Returns:
        Tuple of (intent, value), where intent is one of:
        - empty: blank input
        - slash-empty: input is only '/'
        - slash-command: slash command like '/help' or '/h'
        - slash-prompt: slash prompt invocation like '/summarize' or '/server:summarize'
        - resource: reserved '@' namespace
        - query: plain text query
    """
    normalized = user_input.strip()

    if not normalized:
        return "empty", None

    if normalized.startswith('/'):
        slash_token = normalized[1:].strip()
        if not slash_token:
            return "slash-empty", None

        command = resolve_slash_command(slash_token)
        if command:
            return "slash-command", command

        return "slash-prompt", slash_token

    if normalized.startswith('@'):
        # Reserved for future MCP resource shortcuts.
        return "resource", normalized

    return "query", normalized
