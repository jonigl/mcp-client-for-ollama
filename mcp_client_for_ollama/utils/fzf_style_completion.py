""" FZF-style command completer for interactive mode using prompt_toolkit """
import shutil
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from .constants import INTERACTIVE_COMMANDS
from ..prompts.routing import SLASH_COMMAND_ALIASES


def _build_command_shortcuts() -> dict:
    """Map each canonical command to its shortest alias (e.g. clear -> cc)."""
    shortcuts = {}
    for alias, canonical in SLASH_COMMAND_ALIASES.items():
        if alias == canonical:
            continue
        current = shortcuts.get(canonical)
        if current is None or len(alias) < len(current):
            shortcuts[canonical] = alias
    return shortcuts


COMMAND_SHORTCUTS = _build_command_shortcuts()
# Column width for the shortcut segment: '/' + longest alias
_SHORTCUT_COL_WIDTH = max((len(s) for s in COMMAND_SHORTCUTS.values()), default=0) + 2


class FZFStyleCompleter(Completer):
    """Simple FZF-style completer with fuzzy matching."""

    def __init__(self):
        # Wrap command names with FuzzyCompleter for slash command completion.
        self.command_completer = FuzzyCompleter(WordCompleter(
            list(INTERACTIVE_COMMANDS.keys()),
            ignore_case=True
        ))
        self.prompts = []  # List of prompt info dicts
        self.resources = []  # List of resource info dicts
        self.resource_templates = []  # List of resource template info dicts


    def set_prompts(self, prompts):
        """Set available prompts for completion

        Args:
            prompts: List of prompt info dicts with 'name', 'description', 'arguments'
        """
        self.prompts = prompts

    def _build_action_meta(self, action_type: str, description: str, mime_type: str = "", shortcut: str = "") -> FormattedText:
        """Build action badge metadata for completion rows."""
        _BADGE_COLORS = {
            "prompt":   "#00bcd4",
            "command":  "#ff8c00",
            "static":   "#4caf50",
            "template": "#9c27b0",
        }
        parts = []
        badge_color = _BADGE_COLORS.get(action_type.lower(), "#ff8c00")
        if shortcut:
            parts.append(("fg:#00bcd4 bg:#1e1e1e bold", f" {('/' + shortcut).ljust(_SHORTCUT_COL_WIDTH)}"))
        parts.append((f"fg:#ffffff bg:{badge_color}", f" {action_type} "))
        parts.append(("fg:#d6d6d6 bg:#1e1e1e", f" {description}" if description else ""))
        if mime_type:
            parts += [
                ("fg:#d6d6d6 bg:#1e1e1e", "  "),
                ("fg:#ffffff bg:#546e7a", f" {mime_type} "),
            ]
        return FormattedText(parts)

    def set_resources(self, resources):
        """Set available static resources for completion"""
        self.resources = resources

    def set_resource_templates(self, templates):
        """Set available resource templates for completion"""
        self.resource_templates = templates

    @staticmethod
    def _compute_max_meta_length(min_val=30, max_val=100, fallback=60) -> int:
        """Return a terminal-width-aware max length for completion metadata strings."""
        try:
            return max(min_val, min(max_val, int((shutil.get_terminal_size().columns - 30) * 0.7)))
        except (AttributeError, ValueError):
            return fallback

    def _get_prompt_completions(self, prompt_query):
        """Generate qualified prompt completions for slash namespace.

        Args:
            prompt_query: The token being typed after /

        Yields:
            Completion objects for matching prompts
        """
        # If no prompts available, show a helpful message
        if not self.prompts:
            return

        # Filter and rank prompts by matching
        matches = []
        for prompt in self.prompts:
            name = prompt['name']
            server_name = prompt.get('server', '')
            qualified_name = prompt.get('qualified_name') or f"{server_name}:{name}"
            description = prompt.get('description', '')

            # Simple fuzzy matching
            if (
                prompt_query in qualified_name.lower()
                or prompt_query in name.lower()
                or prompt_query in server_name.lower()
                or (description and prompt_query in description.lower())
            ):
                matches.append(prompt)

        # Return prompt completions
        for prompt in matches:
            name = prompt['name']
            server_name = prompt.get('server', '')
            qualified_name = prompt.get('qualified_name') or f"{server_name}:{name}"
            display_meta = prompt.get('description', '') or ''

            # Get terminal width and calculate max description length
            # Use 60% of terminal width for description, with min 60 and max 200 chars
            try:
                terminal_width = shutil.get_terminal_size().columns
                # Reserve space for prompt name (estimated ~30 chars) and padding
                available_width = terminal_width - 30
                max_desc_length = max(60, min(200, int(available_width * 0.7)))
            except (AttributeError, ValueError):
                # Fallback if terminal size detection fails
                max_desc_length = 100

            # Truncate long descriptions based on terminal width
            if len(display_meta) > max_desc_length:
                display_meta = display_meta[:max_desc_length - 3] + "..."

            display = f"/{qualified_name}"

            # Start position should replace the / and what comes after
            yield Completion(
                qualified_name,
                start_position=-len(prompt_query),
                display=display,
                display_meta=self._build_action_meta("prompt", display_meta)
            )

    def _get_resource_completions(self, resource_query, start_offset=None):
        """Generate completions for resource reads triggered by @.

        Works for both leading-@ (``@file://...``) and mid-input
        (``tell me about @file://...``) positions.

        Args:
            resource_query: The partial URI typed after ``@`` (lowercased).
            start_offset: If given, used as the ``start_position`` for all
                yielded completions. When ``None`` the offset is computed
                from ``-len(resource_query)`` (standard behaviour).
        """
        # Build combined candidate list: static resources + templates
        candidates = []
        for resource in self.resources:
            candidates.append({
                'completion_text': str(resource['uri']),
                'display_uri': str(resource['uri']),
                'name': resource['name'],
                'server': resource.get('server', ''),
                'description': resource.get('description', '') or '',
                'mimeType': resource.get('mimeType', '') or '',
                'is_template': False,
            })
        for template in self.resource_templates:
            candidates.append({
                'completion_text': template['uriTemplate'],
                'display_uri': template['uriTemplate'],
                'name': template['name'],
                'server': template.get('server', ''),
                'description': template.get('description', '') or '',
                'mimeType': template.get('mimeType', '') or '',
                'is_template': True,
            })

        sp = start_offset if start_offset is not None else -len(resource_query)

        if not candidates:
            yield Completion(
                "[no-resources]",
                start_position=sp,
                display=" No resources available",
                display_meta="No resources found from connected MCP servers"
            )
            return

        # Filter by query matching URI/name/description
        matches = [
            c for c in candidates
            if (resource_query in c['display_uri'].lower() or
                resource_query in c['name'].lower() or
                (c['description'] and resource_query in c['description'].lower()))
        ]

        max_meta_length = self._compute_max_meta_length()

        for candidate in matches:
            meta_parts = []
            if candidate['server']:
                meta_parts.append(candidate['server'])
            if candidate['name'] and candidate['name'] != candidate['display_uri']:
                meta_parts.append(candidate['name'])
            if candidate['description']:
                meta_parts.append(candidate['description'])

            description_text = " ".join(meta_parts)
            if len(description_text) > max_meta_length:
                description_text = description_text[:max_meta_length - 3] + "..."

            action_type = "template" if candidate['is_template'] else "static"
            display = f"@{candidate['display_uri']}"

            yield Completion(
                candidate['completion_text'],
                start_position=sp,
                display=display,
                display_meta=self._build_action_meta(action_type, description_text, candidate['mimeType'])
            )

    def _get_command_completions(self, prompt_query, complete_event):
        """Generate completions for interactive commands

        Args:
            prompt_query: The token being typed after /
            complete_event: The completion event

        Yields:
            Completion objects for matching commands
        """
        query_document = Document(text=prompt_query, cursor_position=len(prompt_query))
        for completion in self.command_completer.get_completions(query_document, complete_event):
            cmd = completion.text
            description = INTERACTIVE_COMMANDS.get(cmd, "")
            canonical = SLASH_COMMAND_ALIASES.get(cmd, cmd)
            shortcut = COMMAND_SHORTCUTS.get(canonical, "")

            yield Completion(
                cmd,
                start_position=completion.start_position,
                display=f"/{cmd}",
                display_meta=self._build_action_meta("command", description, shortcut=shortcut)
            )

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        # Slash namespace combines built-in commands and prompts.
        if text_before_cursor.startswith('/'):
            prompt_query = text_before_cursor[1:].lower()
            yielded_any = False

            for completion in self._get_command_completions(prompt_query, complete_event):
                yielded_any = True
                yield completion

            yield from self._get_prompt_completions(prompt_query)
            if not yielded_any and prompt_query == "":
                return

        # Resource completion: find the last '@' that has no whitespace after it.
        # This handles both leading '@uri' and mid-input 'text @uri' forms.
        at_pos = text_before_cursor.rfind('@')
        if at_pos != -1:
            after_at = text_before_cursor[at_pos + 1:]
            if ' ' not in after_at:
                resource_query = after_at.lower()
                # start_position replaces the partial URI after '@'; '@' stays.
                yield from self._get_resource_completions(
                    resource_query, start_offset=-len(after_at)
                )
                return

        # Keep plain query typing free from action autocomplete noise.
        return
