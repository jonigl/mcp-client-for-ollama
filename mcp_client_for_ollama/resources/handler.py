"""Handler for MCP resource interactions."""
import base64
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table

from .parser import extract_template_variables, resolve_template
from ..utils.input import get_input_no_autocomplete

# MIME-type prefixes that should be passed to the model as vision images.
_IMAGE_MIME_PREFIXES = ('image/',)


class ResourceResult:
    """Container for the content read from a single resource.

    Attributes:
        text:   Concatenated text content (empty string if none).
        images: List of base64-encoded image strings for vision models.
    """

    __slots__ = ('text', 'images')

    def __init__(self, text: str = '', images: Optional[List[str]] = None):
        self.text = text
        self.images: List[str] = images or []

    def __bool__(self) -> bool:
        return bool(self.text) or bool(self.images)


class ResourceHandler:
    """Handles resource browsing, reading, and template resolution."""

    def __init__(self, console: Console, resource_manager, server_connector):
        self.console = console
        self.resource_manager = resource_manager
        self.server_connector = server_connector
    # Browsing
    def browse_resources(self):
        """Display all available resources and templates grouped by server."""
        resources_by_server = self.resource_manager.resources_by_server
        templates_by_server = self.resource_manager.templates_by_server

        if not any(resources_by_server.values()) and not any(templates_by_server.values()):
            self.console.print("[yellow]No resources available from connected servers.[/yellow]")
            self.console.print("\n[dim]Press Enter to return to chat...[/dim]")
            input()
            return

        all_servers = sorted(set(list(resources_by_server) + list(templates_by_server)))

        for server_name in all_servers:
            resources = resources_by_server.get(server_name, [])
            templates = templates_by_server.get(server_name, [])
            total = len(resources) + len(templates)
            self.console.print(f"\n[bold cyan]{server_name}[/bold cyan] ({total} item(s))")

            table = Table(show_header=True, header_style="bold magenta", box=None)
            table.add_column("URI / Template", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Type", style="dim")
            table.add_column("Description", style="dim")

            for resource in resources:
                uri = str(resource.uri)
                name = resource.name
                mime_type = getattr(resource, 'mimeType', '') or ''
                description = getattr(resource, 'description', '') or ''
                is_binary = self._is_binary_type(mime_type)
                type_display = f"{mime_type} [red][binary][/red]" if is_binary and mime_type else mime_type
                table.add_row(uri, name, type_display, description)

            for template in templates:
                uri_template = template.uriTemplate
                name = template.name
                mime_type = getattr(template, 'mimeType', '') or ''
                description = getattr(template, 'description', '') or ''
                table.add_row(
                    uri_template,
                    name,
                    f"{mime_type} [yellow][template][/yellow]".strip(),
                    description,
                )

            self.console.print(table)

        self.console.print(
            "\n[dim]Use '@<uri>' in your query to attach a resource, "
            "or type a template URI to fill its variables[/dim]"
        )
        self.console.print("[dim]Press Enter to return to chat...[/dim]")
        input()
    # Reading
    async def read_resource(self, uri: str, sessions: Dict[str, Any]) -> Optional['ResourceResult']:
        """Read a resource by URI and return its content.

        If the URI contains unresolved template variables (``{var}``), the
        user is prompted interactively to fill them in before fetching.

        Args:
            uri: Resource URI to read. May be a template URI with ``{var}``
                 placeholders.
            sessions: Dict mapping server name to session info dicts.

        Returns:
            :class:`ResourceResult` with text and/or images, or ``None`` if
            the resource could not be read.
        """
        # Resolve template variables if present.
        if '{' in uri and '}' in uri:
            resolved = await self.resolve_template_interactive(uri)
            if resolved is None:
                return None
            uri = resolved

        # Try to find the resource in the known static list first.
        static = self.resource_manager.find_resource(uri)
        if static:
            server_name, resource = static
            session_info = sessions.get(server_name)
            if not session_info:
                self.console.print(f"[red]Server '{server_name}' session not found.[/red]")
                return None
            return await self._fetch_and_display(uri, resource.name, session_info['session'])

        # Fallback: try every connected session (handles resolved template URIs
        # and URIs that the server knows about but weren't pre-listed).
        for _server_name, session_info in sessions.items():
            result = await self._fetch_and_display(
                uri, uri, session_info['session'], silent_not_found=True
            )
            if result:
                return result

        # Nothing worked — show a helpful message.
        resource_count = sum(len(r) for r in self.resource_manager.resources_by_server.values())
        self.console.print(f"[yellow]Resource '{uri}' not found.[/yellow]")
        if resource_count == 0:
            self.console.print("[dim]No resources are available from connected servers.[/dim]")
        else:
            self.console.print(
                f"[dim]{resource_count} resource(s) available. "
                "Use 'resources' or 'res' to see them.[/dim]"
            )
        return None

    async def _fetch_and_display(
        self,
        uri: str,
        display_name: str,
        session,
        silent_not_found: bool = False,
    ) -> Optional['ResourceResult']:
        """Fetch resource content from a session and display a brief summary.

        Args:
            uri: Resource URI to read.
            display_name: Human-readable name shown in console messages.
            session: Active MCP client session.
            silent_not_found: When ``True``, suppress error messages (used in
                the fallback loop that tries every session).

        Returns:
            :class:`ResourceResult` on success, or ``None`` on failure /
            empty response.
        """
        try:
            read_result = await session.read_resource(uri)

            if not read_result or not hasattr(read_result, 'contents') or not read_result.contents:
                return None

            text_parts: List[str] = []
            images: List[str] = []

            for content in read_result.contents:
                mime_type = getattr(content, 'mimeType', None) or ''

                if hasattr(content, 'blob') and content.blob:
                    if mime_type.startswith(_IMAGE_MIME_PREFIXES):
                        # MCP blobs are base64 strings per the spec; pass directly.
                        blob = content.blob
                        if isinstance(blob, (bytes, bytearray)):
                            blob = base64.b64encode(blob).decode('ascii')
                        images.append(blob)
                    # Non-image binary content is silently skipped (audio, PDF, etc.)
                elif hasattr(content, 'text') and content.text:
                    text_parts.append(content.text)

            if not text_parts and not images:
                if any(hasattr(c, 'blob') and c.blob for c in read_result.contents):
                    self.console.print(
                        f"[yellow]Resource '{display_name}' contains binary content "
                        "that is not an image — skipped[/yellow]"
                    )
                return None

            text_content = "\n".join(text_parts)
            result = ResourceResult(text=text_content, images=images)

            # Build a human-readable summary line.
            parts = []
            if text_content:
                parts.append(f"{len(text_content)} chars")
            if images:
                parts.append(f"{len(images)} image(s)")
            self.console.print(
                f"[green]✅ Read resource '{display_name}' ({', '.join(parts)})[/green]"
            )

            if text_content:
                preview = text_content[:200] + "..." if len(text_content) > 200 else text_content
                self.console.print(f"\n[dim]Preview:[/dim]\n[dim]{preview}[/dim]\n")

            return result

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            if not silent_not_found:
                self.console.print(f"[red]Error reading resource '{uri}': {str(e)}[/red]")
            return None
    # Template resolution
    async def resolve_template_interactive(self, uri_template: str) -> Optional[str]:
        """Interactively collect variable values to resolve a URI template.

        Prompts the user for each ``{variable}`` placeholder found in
        ``uri_template``. Returns the resolved URI, or ``None`` if the user
        cancels.

        Args:
            uri_template: A URI template string such as ``file:///{path}``.

        Returns:
            Fully resolved URI string, or ``None`` if cancelled.
        """
        variables = extract_template_variables(uri_template)
        if not variables:
            return uri_template  # Nothing to fill in.

        self.console.print(
            f"\n[bold white]Resource template "
            f"[cyan]{uri_template}[/cyan] requires:[/bold white]"
        )

        values: Dict[str, str] = {}
        for var in variables:
            try:
                value = await get_input_no_autocomplete(var)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Resource read cancelled.[/yellow]")
                return None

            if not value or value == 'quit':
                self.console.print("[yellow]Resource read cancelled.[/yellow]")
                return None

            values[var] = value

        return resolve_template(uri_template, values)
    # Helpers
    @staticmethod
    def _is_binary_type(mime_type: str) -> bool:
        """Return True if the MIME type indicates binary (non-text) content."""
        if not mime_type:
            return False
        binary_prefixes = (
            'image/', 'audio/', 'video/', 'application/pdf',
            'application/zip', 'application/octet-stream',
        )
        return any(mime_type.startswith(p) for p in binary_prefixes)
