"""Display utilities for logprobs data from Ollama responses."""
from rich.console import Console
from rich.table import Table
import rich.box


def display_logprobs(console: Console, logprobs_data: list, max_alternatives: int = 3) -> None:
    """Display logprobs data in a formatted Rich table.

    Args:
        console: Rich console for output
        logprobs_data: List of logprob entries from Ollama response
        max_alternatives: Maximum number of alternative tokens to show per position
    """
    if not logprobs_data:
        console.print("[yellow]No logprobs data available. Make sure logprobs is enabled in model-config.[/yellow]")
        return

    # Create a table for logprobs display
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=rich.box.ROUNDED,
        expand=False,
        title="📊 Token Log Probabilities",
        title_style="bold white"
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Token", style="green bold", width=15)
    table.add_column("Logprob", style="cyan", width=10, justify="right")
    table.add_column("Probability", style="yellow", width=12, justify="right")
    table.add_column("Alternatives", style="magenta dim", width=50)

    import math

    for idx, entry in enumerate(logprobs_data, start=1):
        # Handle both dict and object access patterns
        try:
            if hasattr(entry, 'token'):
                # Object access
                token = entry.token
                logprob = entry.logprob
                top_logprobs_list = getattr(entry, 'top_logprobs', []) or []
            else:
                # Dict access
                token = entry.get('token', '')
                logprob = entry.get('logprob', 0)
                top_logprobs_list = entry.get('top_logprobs', []) or []
        except Exception:
            # Skip entries we can't parse
            continue

        # Convert logprob to probability percentage
        probability = math.exp(logprob) * 100

        # Format token display - escape only control chars, show everything else as-is
        token_display = token.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')

        # Format alternatives
        alternatives_text = ""
        if top_logprobs_list:
            alt_parts = []
            for alt in top_logprobs_list[:max_alternatives]:
                try:
                    if hasattr(alt, 'token'):
                        alt_token = alt.token
                        alt_logprob = alt.logprob
                    else:
                        alt_token = alt.get('token', '')
                        alt_logprob = alt.get('logprob', 0)

                    alt_prob = math.exp(alt_logprob) * 100

                    # Skip if it's the same as the chosen token
                    if alt_token == token:
                        continue

                    # Format alternative token display
                    alt_token_display = alt_token.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')

                    alt_parts.append(f"{alt_token_display} ({alt_prob:.1f}%)")
                except Exception:
                    continue

            alternatives_text = ", ".join(alt_parts) if alt_parts else "-"
        else:
            alternatives_text = "-"

        table.add_row(
            str(idx),
            token_display,
            f"{logprob:.3f}",
            f"{probability:.2f}%",
            alternatives_text
        )

    console.print()
    console.print(table)
    console.print()
