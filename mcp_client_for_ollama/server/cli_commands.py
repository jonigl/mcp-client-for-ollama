"""`ollmcp mcp` CLI commands for managing MCP server configurations.

Provides `ollmcp mcp add`, `ollmcp mcp list`, and `ollmcp mcp remove`,
mirroring the `claude mcp` command surface (local/project/user scopes).
"""

from typing import List, Optional

import typer
from rich.console import Console

from . import registry

console = Console()

mcp_app = typer.Typer(
    help="Manage MCP server configurations",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _parse_env(pairs: List[str]) -> dict:
    """Parse repeated KEY=value strings into a dict."""
    env = {}
    for pair in pairs:
        if "=" not in pair:
            console.print(f"[bold red]Error: --env value must be KEY=value, got: {pair}[/bold red]")
            raise typer.Exit(code=1)
        key, value = pair.split("=", 1)
        env[key] = value
    return env


def _parse_headers(pairs: List[str]) -> dict:
    """Parse repeated 'Name: Value' strings into a dict."""
    headers = {}
    for pair in pairs:
        if ":" not in pair:
            console.print(f"[bold red]Error: --header value must be 'Name: Value', got: {pair}[/bold red]")
            raise typer.Exit(code=1)
        name, value = pair.split(":", 1)
        headers[name.strip()] = value.strip()
    return headers


@mcp_app.command("add", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name for the MCP server"),
    transport: str = typer.Option(
        "stdio", "--transport", "-t",
        help="Connection transport: stdio, sse, or http"
    ),
    scope: str = typer.Option(
        registry.SCOPE_LOCAL, "--scope", "-s",
        help="Configuration scope: local (default), project, or user"
    ),
    env: List[str] = typer.Option(
        [], "--env", "-e",
        help="Environment variable for stdio servers, as KEY=value (repeatable)"
    ),
    header: List[str] = typer.Option(
        [], "--header", "-H",
        help="HTTP header for sse/http servers, as 'Name: Value' (repeatable)"
    ),
):
    """Add an MCP server.

    Examples:

      ollmcp mcp add --transport stdio playwright npx @playwright/mcp@latest
      ollmcp mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem /allowed-dir1
      ollmcp mcp add --env API_KEY=YOUR_KEY --transport sse my-sse-server http://localhost:8000/sse
    """
    transport = transport.lower()
    if transport not in ("stdio", "sse", "http"):
        console.print(f"[bold red]Error: --transport must be one of stdio, sse, http (got: {transport})[/bold red]")
        raise typer.Exit(code=1)

    if scope not in registry.SCOPES:
        console.print(f"[bold red]Error: --scope must be one of {', '.join(registry.SCOPES)} (got: {scope})[/bold red]")
        raise typer.Exit(code=1)

    # ctx.args holds everything after `name` not matched by declared options,
    # including anything after a literal `--` separator for stdio commands.
    remainder = list(ctx.args)

    existing = registry.load_scope(scope)
    if name in existing:
        console.print(
            f"[bold red]Error: A server named '{name}' already exists in the '{scope}' scope.[/bold red]\n"
            f"Remove it first with: ollmcp mcp remove {name} --scope {scope}"
        )
        raise typer.Exit(code=1)

    if transport == "stdio":
        if not remainder:
            console.print("[bold red]Error: stdio servers require a command, e.g. ollmcp mcp add <name> -- <command> [args...][/bold red]")
            raise typer.Exit(code=1)
        command, *args = remainder
        entry = {"command": command}
        if args:
            entry["args"] = args
        if env:
            entry["env"] = _parse_env(env)
    else:
        if len(remainder) != 1:
            console.print(f"[bold red]Error: --transport {transport} servers take exactly one <url> argument (got {len(remainder)}).[/bold red]")
            raise typer.Exit(code=1)
        url = remainder[0]
        # Write the standard `.mcp.json` type names ("http"/"sse") for
        # interop with Claude Code and other tools; discovery normalizes
        # "http" to ollmcp's internal "streamable_http" when reading.
        entry = {"type": transport, "url": url}
        if header:
            entry["headers"] = _parse_headers(header)

    registry.add_server(scope, name, entry)
    console.print(f"[green]Added MCP server '{name}' to {scope} scope ({registry.scope_path(scope)})[/green]")


@mcp_app.command("list")
def list_servers():
    """List configured MCP servers, grouped by scope."""
    by_scope = registry.list_by_scope()

    if not any(by_scope.values()):
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print("Add one with: [cyan]ollmcp mcp add --transport http <name> <url>[/cyan]")
        return

    for scope, servers in by_scope.items():
        if not servers:
            continue
        console.print(f"\n[bold]{scope}[/bold] ({registry.scope_path(scope)})")
        for name, entry in servers.items():
            if "url" in entry:
                detail = entry["url"]
            else:
                command = entry.get("command", "")
                args = " ".join(entry.get("args", []))
                detail = f"{command} {args}".strip()
            console.print(f"  [cyan]{name}[/cyan]: {detail}")


@mcp_app.command("remove")
def remove(
    name: str = typer.Argument(..., help="Name of the MCP server to remove"),
    scope: Optional[str] = typer.Option(
        None, "--scope", "-s",
        help="Scope to remove from (default: search local, then project, then user)"
    ),
):
    """Remove an MCP server."""
    if scope is not None and scope not in registry.SCOPES:
        console.print(f"[bold red]Error: --scope must be one of {', '.join(registry.SCOPES)} (got: {scope})[/bold red]")
        raise typer.Exit(code=1)

    found_scope = registry.remove_server(name, scope=scope)
    if found_scope is None:
        if scope:
            console.print(f"[bold red]Error: No server named '{name}' found in the '{scope}' scope.[/bold red]")
        else:
            console.print(f"[bold red]Error: No server named '{name}' found in any scope.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Removed MCP server '{name}' from {found_scope} scope.[/green]")
