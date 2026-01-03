"""Manager for MCP prompts"""
from typing import Dict, List, Optional, Any, Tuple
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

    def find_prompt(self, prompt_name: str) -> Optional[Tuple[str, Any]]:
        """Find a prompt by name (supports both qualified and unqualified names)

        Args:
            prompt_name: Prompt name (e.g., "summarize" or "server.summarize")

        Returns:
            Tuple of (server_name, prompt_object) or None if not found
        """
        # Try exact match with qualified name first (server.prompt_name)
        if '.' in prompt_name:
            server_name, simple_name = prompt_name.rsplit('.', 1)
            prompts = self.prompts_by_server.get(server_name, [])
            for prompt in prompts:
                if prompt.name == simple_name:
                    return (server_name, prompt)

        # Try unqualified name across all servers
        for server_name, prompts in self.prompts_by_server.items():
            for prompt in prompts:
                if prompt.name == prompt_name:
                    return (server_name, prompt)

        return None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all available prompts with their metadata

        Returns:
            List of dicts with prompt info
        """
        prompts = []
        for server_name, server_prompts in self.prompts_by_server.items():
            for prompt in server_prompts:
                qualified_name = f"{server_name}.{prompt.name}"
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
                qualified_name = f"{server_name}.{prompt.name}"
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
