"""Constants used throughout the MCP Client for Ollama application."""

import os
from mcp.types import LATEST_PROTOCOL_VERSION

# Default Claude config file location
DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")

# Default config directory and filename for MCP client for Ollama
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/ollmcp")
if not os.path.exists(DEFAULT_CONFIG_DIR):
    os.makedirs(DEFAULT_CONFIG_DIR)

DEFAULT_CONFIG_FILE = "config.json"

# MCP server registry files managed by `ollmcp mcp add/list/remove`
# User scope: global, available across all projects
USER_MCP_FILE = os.path.join(DEFAULT_CONFIG_DIR, "mcp.json")
# Local scope: private per-project, keyed by absolute working directory
LOCAL_MCP_FILE = os.path.join(DEFAULT_CONFIG_DIR, "mcp.local.json")
# Project scope: shareable file at the project root (current working directory)
PROJECT_MCP_FILENAME = ".mcp.json"

# Default model - Just a placeholder now, the actual default is determined by the user's saved configuration or the first available model in Ollama
DEFAULT_MODEL = "qwen3:0.6b"

# Default ollama lcoal url for API requests
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# Default LLM provider
DEFAULT_PROVIDER = "ollama"

# Reasoning effort levels exposed to the user (excludes "none" which conflicts with thinking-mode
# being the master on/off switch, and any-llm's internal "auto" handling on Ollama is special-cased)
REASONING_EFFORT_LEVELS = ("auto", "minimal", "low", "medium", "high", "xhigh")
DEFAULT_REASONING_EFFORT = "medium"

# Providers ollmcp currently supports: Ollama (native) plus OpenAI and any
# OpenAI-compatible provider (they all use the bundled openai package).
SUPPORTED_PROVIDERS = (
    "ollama, openai, atlascloud, and OpenAI-compatible providers "
    "(openrouter, deepseek, perplexity, etc.)"
)

# Default number of history entries to display when returning from menus
DEFAULT_HISTORY_DISPLAY_LIMIT = 5

# Maximum number of visible completion rows in the completion menu
# This limits the visible rows while still allowing scrolling through all completions
MAX_COMPLETION_MENU_ROWS = 7

# URL for checking package updates on PyPI
PYPI_PACKAGE_URL = "https://pypi.org/pypi/mcp-client-for-ollama/json"

# MCP Protocol Version - Using SDK's latest supported version (currently "2025-11-25")
# The SDK handles backward compatibility with servers on older protocol versions:
# Supported versions: ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
MCP_PROTOCOL_VERSION = LATEST_PROTOCOL_VERSION

# Startup ASCII banner shown when launching ollmcp
OLLMCP_ASCII_ART = r"""
      ___    ___
     /\_ \  /\_ \
  ___\//\ \ \//\ \     ___ ___     ___   _____
 / __`\\ \ \  \ \ \  /' __` __`\  /'___\/\ '__`\
/\ \L\ \\_\ \_ \_\ \_/\ \/\ \/\ \/\ \__/\ \ \L\ \
\ \____//\____\/\____\ \_\ \_\ \_\ \____\\ \ ,__/
 \/___/ \/____/\/____/\/_/\/_/\/_/\/____/ \ \ \/
                                           \ \_\
                                            \/_/
""".strip("\n")

# Interactive commands and their descriptions for autocomplete
INTERACTIVE_COMMANDS = {
    'bye': 'Exit the application',
    'clear-screen': 'Clear terminal screen',
    'clear': 'Clear conversation context',
    'context-info': 'Show context information',
    'context': 'Toggle context retention',
    'exit': 'Exit the application',
    'export-history': 'Export chat history to JSON',
    'full-history': 'View full conversation history',
    'help': 'Show help information',
    'import-history': 'Import chat history from JSON',
    'human-in-the-loop': 'Toggle HIL confirmations',
    'load-config': 'Load saved configuration',
    'loop-limit': 'Set agent max loop limit',
    'model-config': 'Configure model parameters',
    'reasoning-effort': 'Set reasoning effort level',
    'model': 'Select Ollama model',
    'input-mode': 'Switch chat input between single-line and multiline',
    'prompts': 'Browse available MCP prompts',
    'resources': 'Browse available MCP resources',
    'quit': 'Exit the application',
    'reload-servers': 'Reload MCP servers',
    'reset-config': 'Reset to default config',
    'save-config': 'Save current configuration',
    'display-mode': 'Choose plain, markdown, both, or blocks display modes',
    'show-metrics': 'Toggle performance metrics display',
    'show-thinking': 'Toggle thinking visibility',
    'show-tool-execution': 'Toggle tool execution display',
    'thinking-mode': 'Toggle thinking mode',
    'tools': 'Configure available tools'
}

# Default completion menu style (used by prompt_toolkit in interactive mode)
DEFAULT_COMPLETION_STYLE = {
    'prompt': 'ansibrightyellow bold',
    'completion-menu.completion': 'fg:#ffffff bg:#1e1e1e',
    'completion-menu.completion.current': 'fg:#00ff00 bg:#1e1e1e bold',
    'completion-menu.meta': 'fg:#d6d6d6 bg:#1e1e1e',
    'completion-menu.meta.current': 'fg:#ffffff bg:#1e1e1e',
    'completion-menu.meta.completion': 'fg:#d6d6d6 bg:#1e1e1e',
    'completion-menu.meta.completion.current': 'fg:#ffffff bg:#1e1e1e',
    'completion-menu.multi-column-meta': 'fg:#d6d6d6 bg:#1e1e1e',
    'completion-menu.multi-column-meta.current': 'fg:#ffffff bg:#1e1e1e',
    'completion-menu.multi-column-meta.background': 'bg:#1e1e1e',
    'bottom-toolbar': 'fg:#000000 bg:#ffff00 noreverse',
    'bottom-toolbar.text': 'fg:#000000 bg:#ffff00 noreverse',
}
