"""Handler for MCP prompt interactions"""
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt

from .manager import PromptManager
from .display import display_prompt_list, display_prompt_preview
from .content import filter_prompt_messages
from .injection import convert_prompt_messages_to_history
from ..utils.hil_manager import AbortQueryException


class PromptHandler:
    """Handles prompt browsing, invocation, and execution with the model"""

    def __init__(self, console: Console, prompt_manager: PromptManager):
        self.console = console
        self.prompt_manager = prompt_manager

    def browse_prompts(self):
        """Display all available prompts grouped by server"""
        prompts_by_server = self.prompt_manager.get_prompts_by_server()
        display_prompt_list(self.console, prompts_by_server)

        if self.prompt_manager.has_prompts():
            self.console.print("\n[dim]Press Enter to return to chat...[/dim]")
            input()

    async def invoke_prompt(self, prompt_name: str, sessions: Dict[str, Any],
                          process_query_fn, history_context_manager) -> bool:
        """Handle prompt invocation via /prompt_name syntax

        Args:
            prompt_name: Name of the prompt to invoke
            sessions: Dict of server sessions
            process_query_fn: Async function to process the query with injected context
            history_context_manager: Context manager for temporary history extension

        Returns:
            bool: True if prompt was successfully invoked, False otherwise
        """
        if not prompt_name:
            self.console.print("[yellow]Please specify a prompt name after /[/yellow]")
            return False

        # Find the prompt
        result = self.prompt_manager.find_prompt(prompt_name)
        if not result:
            self.console.print(f"[yellow]Prompt '{prompt_name}' not found. Use 'prompts' to see available prompts.[/yellow]")
            return False

        server_name, prompt = result

        # Collect arguments if needed
        arg_values = await self._collect_prompt_arguments(prompt)
        if arg_values is None:  # User cancelled
            return False

        # Get the prompt content from the server
        try:
            session_info = sessions.get(server_name)
            if not session_info:
                self.console.print(f"[red]Server '{server_name}' session not found.[/red]")
                return False

            session = session_info['session']
            prompt_result = await session.get_prompt(prompt.name, arg_values)

            # Filter messages to text-only
            messages = prompt_result.messages if hasattr(prompt_result, 'messages') else []
            filtered_messages, skipped_types = filter_prompt_messages(messages)

            if not filtered_messages:
                self.console.print("[yellow]Prompt returned no text content.[/yellow]")
                return False

            # Display preview
            display_prompt_preview(self.console, prompt.name, server_name, filtered_messages, skipped_types)

            # Get confirmation
            confirmation_result = await self._get_prompt_confirmation(filtered_messages)
            if confirmation_result == "cancel":
                return False

            # Check if prompt ends with user or assistant message
            last_message = filtered_messages[-1]

            # Handle inject-only mode
            if confirmation_result == "inject":
                converted_entries = convert_prompt_messages_to_history(filtered_messages)
                with history_context_manager(converted_entries):
                    injected_count = len(filtered_messages)
                    self.console.print(f"[green]✅ Injected {injected_count} message(s) from prompt '{prompt.name}' to history.[/green]")
                    self.console.print("[cyan]Type your query to continue the conversation...[/cyan]\n")
                return True

            # Execute with rollback on error
            injected_count = len(filtered_messages)
            self.console.print(f"[green]✅ Injecting {injected_count} message(s) from prompt '{prompt.name}'...[/green]\n")

            if last_message['role'] == 'user':
                # Prompt ends with user message - use it as the query
                # Convert all messages except the last one to history context
                context_messages = filtered_messages[:-1] if len(filtered_messages) > 1 else []
                converted_entries = convert_prompt_messages_to_history(context_messages)
                query_to_process = last_message['content']
            else:
                # Prompt ends with assistant message - inject all and add follow-up query
                converted_entries = convert_prompt_messages_to_history(filtered_messages)
                query_to_process = "Please respond based on the above context."

            with history_context_manager(converted_entries):
                await process_query_fn(query_to_process)

            return True

        except AbortQueryException:
            # User aborted during prompt execution
            self.console.print("[yellow]Prompt injection reverted.[/yellow]")
            return False

        except Exception as e:
            self.console.print(f"[red]Error fetching or processing prompt: {str(e)}[/red]")
            return False

    async def _collect_prompt_arguments(self, prompt) -> Optional[Dict[str, str]]:
        """Collect required arguments from user

        Args:
            prompt: Prompt object with arguments attribute

        Returns:
            Dict of argument values, or None if user cancelled
        """
        arguments = getattr(prompt, 'arguments', []) or []
        required_args = [arg for arg in arguments if getattr(arg, 'required', False)]

        arg_values = {}
        if required_args:
            self.console.print(f"\n[bold white]Prompt [cyan]{prompt.name}[/cyan] requires arguments:[/bold white]")
            for arg in required_args:
                arg_name = arg.name
                arg_desc = getattr(arg, 'description', '')

                # Print description on separate line if available
                if arg_desc and arg_desc != arg_name:
                    self.console.print(f"[white]{arg_desc}[/white]")

                try:
                    self.console.print(f"[bold yellow]{arg_name}❯[/bold yellow] ", end="")
                    value = input()
                except (KeyboardInterrupt, EOFError):
                    self.console.print("\n[yellow]Prompt invocation cancelled.[/yellow]")
                    return None

                if not value or value.strip() == "":
                    self.console.print("[yellow]Prompt invocation cancelled.[/yellow]")
                    return None

                arg_values[arg_name] = value

        return arg_values

    async def _get_prompt_confirmation(self, filtered_messages: list) -> str:
        """Get user confirmation before injecting prompt

        Args:
            filtered_messages: List of filtered prompt messages

        Returns:
            str: 'proceed' to execute, 'inject' to inject only, 'cancel' to abort
        """
        self.console.print("\n[bold yellow]🧑‍💻 Prompt Injection Confirmation[/bold yellow]")
        self.console.print()

        # Check if prompt ends with user or assistant message
        last_message = filtered_messages[-1]
        ends_with_user = last_message['role'] == 'user'

        # Display context-aware information
        if not ends_with_user:
            # Show what query will be used for assistant-ending prompts
            self.console.print("[dim]If yes is selected, will use query: 'Please respond based on the above context.'[/dim]")
            self.console.print()

        # Display options
        self.console.print("[bold cyan]Options:[/bold cyan]")
        self.console.print("  [green]y/yes[/green] - Send query to model (default)")
        self.console.print("  [cyan]i/inject[/cyan] - Just add to history, type your own query")
        self.console.print("  [red]n/no[/red] - Cancel and return to chat")
        self.console.print()

        try:
            choice = Prompt.ask(
                "[bold]What would you like to do?[/bold]",
                choices=["y", "yes", "i", "inject", "n", "no"],
                default="y",
                show_choices=False
            ).lower()
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Prompt injection cancelled.[/yellow]")
            return "cancel"

        if choice in ["n", "no"]:
            self.console.print("[yellow]Prompt injection cancelled.[/yellow]")
            return "cancel"
        elif choice in ["i", "inject"]:
            return "inject"
        else:
            # y/yes
            return "proceed"
