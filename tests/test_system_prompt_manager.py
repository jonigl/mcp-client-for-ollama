"""Test for System Prompt Manager functionality"""

import os
import tempfile
import pytest
from unittest.mock import Mock
from mcp_client_for_ollama.prompts.system_prompt_manager import (
    SystemPromptManager,
    SystemPrompt,
)


class TestSystemPromptManager:
    """Test cases for SystemPromptManager"""

    def test_initialization(self):
        """Test that SystemPromptManager initializes correctly"""
        console = Mock()
        manager = SystemPromptManager(console)

        assert manager.active_index == -1
        assert manager.available_prompts == {}
        assert manager.prompt_names == []

    def test_create_default_prompt(self):
        """Test creating default.md prompt"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SystemPromptManager(console, config_dir=tmpdir)

            # Create default with custom content
            content = "You are a helpful coding assistant."
            result = manager.create_default_prompt(content)

            assert result is True
            assert os.path.exists(os.path.join(tmpdir, "system_prompts", "default.md"))

            # Read and verify content
            with open(os.path.join(tmpdir, "system_prompts", "default.md"), "r") as f:
                assert content in f.read()

    def test_load_prompts_from_directory(self):
        """Test loading prompts from directory"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "system_prompts")
            os.makedirs(prompts_dir)

            # Create test prompt files
            with open(os.path.join(prompts_dir, "plan.md"), "w") as f:
                f.write("# Planning Mode\n\nYou are a planning assistant.")

            with open(os.path.join(prompts_dir, "build.md"), "w") as f:
                f.write("# Build Mode\n\nYou are a build assistant.")

            manager = SystemPromptManager(console, config_dir=tmpdir)
            manager.load_prompts_from_directory()

            assert "plan" in manager.list_prompts()
            assert "build" in manager.list_prompts()
            assert len(manager.list_prompts()) == 2

    def test_cycle_prompts(self):
        """Test cycling through prompts with next/previous"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "system_prompts")
            os.makedirs(prompts_dir)

            # Create test prompt files
            for name in ["alpha", "beta", "gamma"]:
                with open(os.path.join(prompts_dir, f"{name}.md"), "w") as f:
                    f.write(f"# {name}")

            manager = SystemPromptManager(console, config_dir=tmpdir)
            manager.load_prompts_from_directory()

            # Test cycling forward
            first = manager.next_prompt()
            assert first == "alpha"

            second = manager.next_prompt()
            assert second == "beta"

            third = manager.next_prompt()
            assert third == "gamma"

            # Should cycle back to alpha
            fourth = manager.next_prompt()
            assert fourth == "alpha"

    def test_cycle_previous_prompts(self):
        """Test cycling backward through prompts"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "system_prompts")
            os.makedirs(prompts_dir)

            # Create test prompt files
            for name in ["alpha", "beta", "gamma"]:
                with open(os.path.join(prompts_dir, f"{name}.md"), "w") as f:
                    f.write(f"# {name}")

            manager = SystemPromptManager(console, config_dir=tmpdir)
            manager.load_prompts_from_directory()

            # Start at alpha
            manager.set_active_prompt("alpha")

            # Test cycling backward
            prev = manager.previous_prompt()
            assert prev == "gamma"  # Should wrap around

            prev = manager.previous_prompt()
            assert prev == "beta"

    def test_get_active_prompt_content(self):
        """Test getting active prompt content"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "system_prompts")
            os.makedirs(prompts_dir)

            content = "You are a helpful assistant."
            with open(os.path.join(prompts_dir, "default.md"), "w") as f:
                f.write(content)

            manager = SystemPromptManager(console, config_dir=tmpdir)
            manager.load_prompts_from_directory()
            manager.set_active_prompt("default")

            assert manager.get_active_prompt_content() == content

    def test_set_active_prompt_none(self):
        """Test setting active prompt to None"""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "system_prompts")
            os.makedirs(prompts_dir)

            with open(os.path.join(prompts_dir, "test.md"), "w") as f:
                f.write("test content")

            manager = SystemPromptManager(console, config_dir=tmpdir)
            manager.load_prompts_from_directory()

            # Set to test first
            manager.set_active_prompt("test")
            assert manager.get_active_prompt_name() == "test"

            # Set to None
            manager.set_active_prompt(None)
            assert manager.get_active_prompt_name() is None
            assert manager.get_active_prompt_content() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
