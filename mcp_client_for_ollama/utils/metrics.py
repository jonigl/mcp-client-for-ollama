"""
Metrics display utilities for the MCP client for Ollama.

This module provides functions for extracting and displaying performance metrics from Ollama responses.
"""
from rich.panel import Panel

def extract_metrics(chunk):
    """Extract metrics from an Ollama response chunk

    Args:
        chunk: Response chunk from Ollama that may contain metrics

    Returns:
        dict: Dictionary containing extracted metrics, or None if no metrics available
    """
    if not (hasattr(chunk, 'done') and chunk.done):
        return None

    return {
        'total_duration': getattr(chunk, 'total_duration', None),
        'load_duration': getattr(chunk, 'load_duration', None),
        'prompt_eval_count': getattr(chunk, 'prompt_eval_count', None),
        'prompt_eval_duration': getattr(chunk, 'prompt_eval_duration', None),
        'eval_count': getattr(chunk, 'eval_count', None),
        'eval_duration': getattr(chunk, 'eval_duration', None)
    }

def display_metrics(console, metrics):
    """Display performance metrics in a formatted way

    Args:
        console: Rich console for output
        metrics: Dictionary containing metrics from Ollama response
    """
    if not metrics:
        return

    # Convert nanoseconds to seconds for durations
    def ns_to_seconds(ns_value):
        return ns_value / 1_000_000_000 if ns_value else 0

    total_duration = ns_to_seconds(metrics.get('total_duration'))
    load_duration = ns_to_seconds(metrics.get('load_duration'))
    prompt_eval_duration = ns_to_seconds(metrics.get('prompt_eval_duration'))
    eval_duration = ns_to_seconds(metrics.get('eval_duration'))

    prompt_eval_count = metrics.get('prompt_eval_count', 0)
    eval_count = metrics.get('eval_count', 0)

    # Build metrics content
    metrics_lines = []

    # Display basic metrics
    if total_duration > 0:
        metrics_lines.append(f"[cyan]total duration:[/cyan]       {total_duration:.9f}s")
    if load_duration > 0:
        metrics_lines.append(f"[cyan]load duration:[/cyan]        {load_duration * 1000:.6f}ms")
    if prompt_eval_count:
        metrics_lines.append(f"[cyan]prompt eval count:[/cyan]    {prompt_eval_count} token(s)")
    if prompt_eval_duration > 0:
        metrics_lines.append(f"[cyan]prompt eval duration:[/cyan] {prompt_eval_duration * 1000:.6f}ms")
    if eval_count:
        metrics_lines.append(f"[cyan]eval count:[/cyan]           {eval_count} token(s)")
    if eval_duration > 0:
        metrics_lines.append(f"[cyan]eval duration:[/cyan]        {eval_duration:.9f}s")

    # Calculate and display rates
    if prompt_eval_count and prompt_eval_duration > 0:
        prompt_eval_rate = prompt_eval_count / prompt_eval_duration
        metrics_lines.append(f"[green]prompt eval rate:[/green]     {prompt_eval_rate:.2f} tokens/s")

    if eval_count and eval_duration > 0:
        eval_rate = eval_count / eval_duration
        metrics_lines.append(f"[green]eval rate:[/green]            {eval_rate:.2f} tokens/s")

    # Display metrics in a panel
    if metrics_lines:
        console.print()  # Add spacing before panel
        metrics_content = "\n".join(metrics_lines)
        console.print(Panel(
            metrics_content,
            title="📊 Performance Metrics",
            border_style="violet",
            expand=False
        ))
        console.print()  # Add spacing after panel
