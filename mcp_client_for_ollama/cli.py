#!/usr/bin/env python
"""Command-line interface for the MCP Client for Ollama."""

from .client import app

def run_cli():
    """Run the MCP Client for Ollama command-line interface."""
    app()

if __name__ == "__main__":
    run_cli()
