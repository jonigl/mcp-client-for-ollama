"""Human-in-the-Loop (HIL) manager for tool execution confirmations.

This module manages HIL confirmations for tool calls, allowing users to review,
approve, or skip tool executions before they are performed.
"""

from rich.prompt import Prompt
from rich.console import Console


class AbortQueryException(Exception):
    """Exception raised when user chooses to abort the current query.

    This signals that the query should be stopped and not saved to history.
    """
    pass


class HumanInTheLoopManager:
    """Manages Human-in-the-Loop confirmations for tool execution"""

    def __init__(self, console: Console):
        """Initialize the HIL manager.

        Args:
            console: Rich console for output
        """
        self.console = console
        # Store HIL settings locally since there's no persistent config object
        self._hil_enabled = True  # Default to enabled
        # Per-query/session option to auto-execute tools without asking for
        # the remainder of the current model/query process. This is not
        # persisted and resets between queries.
        self._session_auto_execute = False

    def is_enabled(self) -> bool:
        """Check if HIL confirmations are enabled"""
        return self._hil_enabled

    def toggle(self) -> None:
        """Toggle HIL confirmations"""
        if self.is_enabled():
            self.set_enabled(False)
        else:
            self.set_enabled(True)
            self.console.print("[green]🧑‍💻 HIL confirmations enabled[/green]")
            self.console.print("[dim]You will be prompted to confirm each tool call.[/dim]")

    def set_enabled(self, enabled: bool) -> None:
        """Set HIL enabled state (used when loading from config)"""
        self._hil_enabled = enabled

    def set_session_auto_execute(self, enabled: bool) -> None:
        """Enable or disable session-level auto-execution.

        When enabled, tool confirmations will be skipped for the remainder
        of the current query/process session. This is not persisted.
        """
        self._session_auto_execute = enabled

    def reset_session(self) -> None:
        """Reset any per-query/session HIL state.

        Call this between model/query process loops to ensure session
        options don't leak into subsequent queries.
        """
        self._session_auto_execute = False

    async def request_tool_confirmation(self, tool_name: str, tool_args: dict) -> bool:
        """
        Request user confirmation for tool execution

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            bool: should_execute
        """
        if not self.is_enabled():
            return True  # Execute if HIL is disabled

        # If the session-level auto-execute has been enabled earlier in
        # this query/process, skip prompting and execute automatically.
        if self._session_auto_execute:
            return True

        self.console.print("\n[bold yellow]🧑‍💻 Human-in-the-Loop Confirmation[/bold yellow]")

        # Show tool information
        self.console.print(f"[cyan]Tool to execute:[/cyan] [bold]{tool_name}[/bold]")

        # Show arguments
        if tool_args:
            self.console.print("[cyan]Arguments:[/cyan]")
            for key, value in tool_args.items():
                # Truncate long values for display
                display_value = str(value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                self.console.print(f"  • {key}: {display_value}")
        else:
            self.console.print("[cyan]Arguments:[/cyan] [dim]None[/dim]")

        self.console.print()

        # Display options
        self._display_confirmation_options()

        choice = Prompt.ask(
            "[bold]What would you like to do?[/bold]",
            choices=["y", "yes", "n", "no", "s", "session", "d", "disable", "a", "abort"],
            default="y",
            show_choices=False
        ).lower()

        return self._handle_user_choice(choice)

    def _display_confirmation_options(self) -> None:
        """Display available confirmation options"""
        self.console.print("[bold cyan]Options:[/bold cyan]")
        self.console.print("  [green]y/yes[/green] - Execute the tool call")
        self.console.print("  [red]n/no[/red] - Skip this tool call")
        self.console.print("  [magenta]s/session[/magenta] - Execute without asking for this session")
        self.console.print("  [yellow]d/disable[/yellow] - Disable HIL confirmations permanently")
        self.console.print("  [bold red]a/abort[/bold red] - Abort this query (won't save to history)")
        self.console.print()

    def _handle_user_choice(self, choice: str) -> bool:
        """
        Handle user's confirmation choice

        Args:
            choice: User's choice string

        Returns:
            bool: should_execute
        """
        if choice in ["d", "disable"]:
            # Notify user that it can be re-enabled
            self.console.print("\n[yellow]Tool calls will proceed automatically without confirmation.[/yellow]")
            self.console.print("[cyan]You can re-enable this with the command: human-in-loop or hil[/cyan]\n")

            # Ask for confirmation to disable permanently
            execute_current = Prompt.ask(
                "[bold]Are you sure you want to disable HIL confirmations permanently?[/bold]",
                choices=["y", "yes", "n", "no"],
                default="y"
            ).lower()

            should_execute = execute_current in ["y", "yes"]
            if should_execute:
                self.toggle()  # Disable HIL
                self.console.print("[yellow]🤖 HIL confirmations disabled[/yellow]")
            return should_execute

        elif choice in ["s", "session"]:
            self.set_session_auto_execute(True)
            self.console.print("[magenta]🧑‍💻 Tool calls will proceed automatically for the remainder of this session.[/magenta]")
            return True

        elif choice in ["a", "abort"]:
            self.console.print("[bold red]🛑 Aborting query...[/bold red]")
            raise AbortQueryException("Query aborted by user during tool confirmation")

        elif choice in ["n", "no"]:
            self.console.print("[yellow]⏭️  Tool call skipped[/yellow]")
            self.console.print("[dim]Tip: Use 'human-in-loop' or 'hil' to disable these confirmations permanently[/dim]")
            return False

        else:  # y/yes
            self.console.print("[dim]Tip: Use 'human-in-loop' or 'hil' to disable these confirmations[/dim]")
            return True
