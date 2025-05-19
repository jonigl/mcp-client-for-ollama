"""
Main entry point for the MCP Client for Ollama when run as a module.

This allows you to run the client using:
    python -m mcp_client_for_ollama

It simply imports and runs the main function from cli.py.
"""

import asyncio
from .cli import main

if __name__ == "__main__":
    asyncio.run(main())
