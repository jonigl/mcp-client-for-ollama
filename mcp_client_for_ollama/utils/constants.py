"""Constants used throughout the MCP Client for Ollama application."""

import os

# Default Claude config file location
DEFAULT_CLAUDE_CONFIG = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")

# Default config directory and filename for MCP client for Ollama
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/ollmcp")
if not os.path.exists(DEFAULT_CONFIG_DIR):
    os.makedirs(DEFAULT_CONFIG_DIR)

DEFAULT_CONFIG_FILE = "config.json"

# Default model
DEFAULT_MODEL = "qwen2.5:7b"

# Default ollama lcoal url for API requests
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


# URL for checking package updates on PyPI
PYPI_PACKAGE_URL = "https://pypi.org/pypi/mcp-client-for-ollama/json"

# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2025-06-18"

# Interactive commands and their descriptions for autocomplete
INTERACTIVE_COMMANDS = {
    'tools': 'Configure available tools',
    'help': 'Show help information',
    'model': 'Select Ollama model',
    'model-config': 'Configure model parameters',
    'context': 'Toggle context retention',
    'thinking-mode': 'Toggle thinking mode',
    'show-thinking': 'Toggle thinking visibility',
    'show-tool-execution': 'Toggle tool execution display',
    'show-metrics': 'Toggle performance metrics display',
    'clear': 'Clear conversation context',
    'context-info': 'Show context information',
    'clear-screen': 'Clear terminal screen',
    'save-config': 'Save current configuration',
    'load-config': 'Load saved configuration',
    'reset-config': 'Reset to default config',
    'reload-servers': 'Reload MCP servers',
    'human-in-the-loop': 'Toggle HIL confirmations',
    'agent': 'Manage specialized agents',
    'list-agents': 'List all agents',
    'quit': 'Exit the application',
    'exit': 'Exit the application',
    'bye': 'Exit the application'
}

# Default completion menu style (used by prompt_toolkit in interactive mode)
DEFAULT_COMPLETION_STYLE = {
    'prompt': 'ansibrightyellow bold',
    'completion-menu.completion': 'bg:#1e1e1e #ffffff',
    'completion-menu.completion.current': 'bg:#1e1e1e #00ff00 bold reverse',
    'completion-menu.meta': 'bg:#1e1e1e #888888 italic',
    'completion-menu.meta.current': 'bg:#1e1e1e #ffffff italic reverse',
    'bottom-toolbar': 'reverse',
}
