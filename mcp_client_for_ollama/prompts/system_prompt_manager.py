"""Manager for external system prompt files (.md files)"""

import os
import glob
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SystemPrompt:
    """Represents a system prompt loaded from a file"""

    name: str
    content: str
    filepath: str


class SystemPromptManager:
    """Manages external system prompt files from a directory.

    This class handles loading, cycling, and managing system prompts stored
    as .md files in a designated directory.
    """

    def __init__(self, console, config_dir: Optional[str] = None):
        """Initialize the SystemPromptManager.

        Args:
            console: Rich console for output
            config_dir: Base configuration directory (defaults to ~/.config/ollmcp)
        """
        self.console = console
        self.config_dir = config_dir or os.path.expanduser("~/.config/ollmcp")
        self.prompts_dir = os.path.join(self.config_dir, "system_prompts")
        self.available_prompts: Dict[str, SystemPrompt] = {}
        self.prompt_names: List[str] = []  # Ordered list for cycling
        self.active_index: int = -1  # -1 means no active prompt

    def load_prompts_from_directory(self, directory: Optional[str] = None):
        """Load all .md files from the prompts directory.

        Args:
            directory: Directory to load from (defaults to self.prompts_dir)
        """
        search_dir = directory or self.prompts_dir
        self.available_prompts.clear()
        self.prompt_names.clear()
        self.active_index = -1

        if not os.path.exists(search_dir):
            os.makedirs(search_dir, exist_ok=True)
            return

        # Load all .md files
        md_files = sorted(glob.glob(os.path.join(search_dir, "*.md")))
        for filepath in md_files:
            name = Path(filepath).stem  # filename without extension
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.available_prompts[name] = SystemPrompt(
                    name=name, content=content, filepath=filepath
                )
                self.prompt_names.append(name)
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Could not load prompt file {filepath}: {e}[/yellow]"
                )

    def create_default_prompt(self, content: str = "") -> bool:
        """Create the default.md prompt file with given content.

        Args:
            content: Content for the default prompt

        Returns:
            bool: True if created successfully or already exists
        """
        os.makedirs(self.prompts_dir, exist_ok=True)
        default_path = os.path.join(self.prompts_dir, "default.md")

        if os.path.exists(default_path):
            return True

        try:
            with open(default_path, "w", encoding="utf-8") as f:
                f.write(
                    content
                    if content
                    else "# Default System Prompt\n\nYou are a helpful assistant."
                )
            return True
        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Could not create default.md: {e}[/yellow]"
            )
            return False

    def get_active_prompt_content(self) -> Optional[str]:
        """Get the content of the currently active prompt.

        Returns:
            str: Content of active prompt, or None if no prompt is active
        """
        if self.active_index < 0 or self.active_index >= len(self.prompt_names):
            return None

        active_name = self.prompt_names[self.active_index]
        prompt = self.available_prompts.get(active_name)
        return prompt.content if prompt else None

    def get_active_prompt_name(self) -> Optional[str]:
        """Get the name of the currently active prompt.

        Returns:
            str: Name of active prompt, or None if no prompt is active
        """
        if self.active_index < 0 or self.active_index >= len(self.prompt_names):
            return None
        return self.prompt_names[self.active_index]

    def set_active_prompt(self, name: Optional[str]) -> bool:
        """Set the active prompt by name.

        Args:
            name: Name of the prompt to activate, or None to disable

        Returns:
            bool: True if successfully set, False if prompt not found
        """
        if name is None:
            self.active_index = -1
            return True

        if name in self.available_prompts:
            self.active_index = self.prompt_names.index(name)
            return True
        return False

    def next_prompt(self) -> Optional[str]:
        """Cycle to the next prompt (TAB functionality).

        Returns:
            str: Name of the newly active prompt, or None if no prompts available
        """
        if not self.prompt_names:
            return None

        if self.active_index < 0:
            self.active_index = 0
        else:
            self.active_index = (self.active_index + 1) % len(self.prompt_names)

        return self.prompt_names[self.active_index]

    def previous_prompt(self) -> Optional[str]:
        """Cycle to the previous prompt (Shift+TAB functionality).

        Returns:
            str: Name of the newly active prompt, or None if no prompts available
        """
        if not self.prompt_names:
            return None

        if self.active_index < 0:
            self.active_index = len(self.prompt_names) - 1
        else:
            self.active_index = (self.active_index - 1) % len(self.prompt_names)

        return self.prompt_names[self.active_index]

    def list_prompts(self) -> List[str]:
        """Get list of available prompt names.

        Returns:
            list: Sorted list of prompt names
        """
        return self.prompt_names.copy()

    def has_prompts(self) -> bool:
        """Check if any prompts are available.

        Returns:
            bool: True if prompts are available
        """
        return len(self.prompt_names) > 0

    def get_prompts_dir(self) -> str:
        """Get the prompts directory path.

        Returns:
            str: Path to the system prompts directory
        """
        return self.prompts_dir
