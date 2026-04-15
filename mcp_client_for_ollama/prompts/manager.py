"""Manager for MCP prompts"""
from typing import Dict, List, Any, Tuple
from rich.console import Console


class PromptManager:
    """Manages MCP prompts from multiple servers"""

    def __init__(self, console: Console):
        self.console = console
        self.prompts_by_server: Dict[str, List[Any]] = {}  # Single source of truth

    def set_prompts(self, prompts_by_server: Dict[str, List[Any]]):
        """Set available prompts from all servers

        Args:
            prompts_by_server: Dict mapping server name to list of Prompt objects
        """
        self.prompts_by_server = prompts_by_server

    def find_prompt_matches(self, prompt_name: str) -> List[Tuple[str, Any]]:
        """Find all server matches for an unqualified prompt name."""
        matches: List[Tuple[str, Any]] = []
        for server_name, prompts in self.prompts_by_server.items():
            for prompt in prompts:
                if prompt.name == prompt_name:
                    matches.append((server_name, prompt))
        return matches

    def resolve_prompt_reference(self, prompt_reference: str) -> Dict[str, Any]:
        """Resolve a prompt reference with explicit ambiguity handling.

        Args:
            prompt_reference: Prompt ref like "summarize" or "server:summarize"

        Returns:
            Dict with status and additional resolution data.
            Status values: resolved, ambiguous, not-found, invalid.
        """
        normalized = prompt_reference.strip()
        if not normalized:
            return {
                "status": "invalid",
                "reason": "empty",
                "requested": normalized,
            }

        if ':' in normalized:
            server_name, prompt_name = normalized.rsplit(':', 1)
            if not server_name or not prompt_name:
                return {
                    "status": "invalid",
                    "reason": "malformed-qualified",
                    "requested": normalized,
                }

            prompts = self.prompts_by_server.get(server_name, [])
            for prompt in prompts:
                if prompt.name == prompt_name:
                    return {
                        "status": "resolved",
                        "requested": normalized,
                        "server_name": server_name,
                        "prompt": prompt,
                    }

            return {
                "status": "not-found",
                "requested": normalized,
                "qualified": True,
                "server_name": server_name,
                "prompt_name": prompt_name,
                "server_exists": server_name in self.prompts_by_server,
            }

        matches = self.find_prompt_matches(normalized)
        if len(matches) == 1:
            server_name, prompt = matches[0]
            return {
                "status": "resolved",
                "requested": normalized,
                "server_name": server_name,
                "prompt": prompt,
            }

        if len(matches) > 1:
            candidates = sorted(f"{server_name}:{prompt.name}" for server_name, prompt in matches)
            return {
                "status": "ambiguous",
                "requested": normalized,
                "candidates": candidates,
            }

        return {
            "status": "not-found",
            "requested": normalized,
            "qualified": False,
        }

    def get_prompt_names_for_server(self, server_name: str) -> List[str]:
        """Get all prompt names for a specific server."""
        prompts = self.prompts_by_server.get(server_name, [])
        return sorted(prompt.name for prompt in prompts)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all available prompts with their metadata

        Returns:
            List of dicts with prompt info
        """
        prompts = []
        for server_name, server_prompts in self.prompts_by_server.items():
            for prompt in server_prompts:
                qualified_name = f"{server_name}:{prompt.name}"
                prompts.append({
                    'qualified_name': qualified_name,
                    'name': prompt.name,
                    'server': server_name,
                    'description': getattr(prompt, 'description', None),
                    'arguments': getattr(prompt, 'arguments', [])
                })
        return prompts

    def get_prompts_by_server(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get prompts grouped by server

        Returns:
            Dict mapping server name to list of prompt info dicts
        """
        result = {}
        for server_name, prompts in self.prompts_by_server.items():
            result[server_name] = []
            for prompt in prompts:
                qualified_name = f"{server_name}:{prompt.name}"
                result[server_name].append({
                    'qualified_name': qualified_name,
                    'name': prompt.name,
                    'description': getattr(prompt, 'description', None),
                    'arguments': getattr(prompt, 'arguments', [])
                })
        return result

    def get_prompt_count(self) -> int:
        """Get total number of available prompts"""
        return sum(len(prompts) for prompts in self.prompts_by_server.values())

    def has_prompts(self) -> bool:
        """Check if any prompts are available"""
        return any(self.prompts_by_server.values())
