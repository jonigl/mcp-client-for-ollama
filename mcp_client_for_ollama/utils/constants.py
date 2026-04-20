"""Constants used throughout the MCP Client for Ollama application."""

import os
import platform
from mcp.types import LATEST_PROTOCOL_VERSION

# Default Claude config file location
if os.name == 'nt':
    # %appdata% typically resolves as C:\Users\<USERNAME>\AppData\Roaming
    APPDATA = os.environ['APPDATA']
    CONFIG_DIR = os.path.join(APPDATA, 'Claude', 'claude_desktop_config.json')
else:
    CONFIG_DIR =  (
        os.path.expanduser("~/Library/Application Support/Claude")
        if platform.system() != 'Linux'
        else os.path.expanduser("~/.config/Claude")
    )
DEFAULT_CLAUDE_CONFIG = os.path.join(CONFIG_DIR, "claude_desktop_config.json")

# Default config directory and filename for MCP client for Ollama
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/ollmcp")
if not os.path.exists(DEFAULT_CONFIG_DIR):
    os.makedirs(DEFAULT_CONFIG_DIR)

DEFAULT_CONFIG_FILE = "config.json"

# Default model
DEFAULT_MODEL = "qwen2.5:7b"

# Default ollama lcoal url for API requests
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

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
    'model': 'Select Ollama model',
    'prompts': 'Browse available MCP prompts',
    'quit': 'Exit the application',
    'reload-servers': 'Reload MCP servers',
    'reset-config': 'Reset to default config',
    'save-config': 'Save current configuration',
    'display-mode': 'Choose plain, markdown, or both display modes',
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
    'bottom-toolbar': 'reverse',
}
