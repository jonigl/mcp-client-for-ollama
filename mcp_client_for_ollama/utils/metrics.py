"""
Metrics display utilities for the MCP client.

This module provides functions for extracting and displaying token usage
from streaming LLM responses.
"""
from rich.panel import Panel


def extract_metrics(chunk):
    """Extract token usage from a streaming chunk.

    Args:
        chunk: A ChatCompletionChunk that may carry a usage field.

    Returns:
        dict: Token usage counts, or None if the chunk has no usage data.
    """
    usage = getattr(chunk, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def display_metrics(console, metrics):
    """Display token usage in a formatted panel.

    Args:
        console: Rich console for output
        metrics: Dictionary containing token usage from the response
    """
    if not metrics:
        return

    prompt_tokens = metrics.get("prompt_tokens") or 0
    completion_tokens = metrics.get("completion_tokens") or 0
    total_tokens = metrics.get("total_tokens") or 0

    if not any([prompt_tokens, completion_tokens, total_tokens]):
        return

    lines = []
    if prompt_tokens:
        lines.append(f"[cyan]prompt tokens:[/cyan]     {prompt_tokens}")
    if completion_tokens:
        lines.append(f"[cyan]completion tokens:[/cyan] {completion_tokens}")
    if total_tokens:
        lines.append(f"[cyan]total tokens:[/cyan]      {total_tokens}")

    console.print()
    console.print(Panel(
        "\n".join(lines),
        title="📊 Token Usage",
        border_style="violet",
        expand=False,
    ))
    console.print()
