"""Tests for ModelManager.resolve_initial_model() and print_resolution_status()."""

import unittest
from unittest.mock import AsyncMock

from rich.console import Console

from mcp_client_for_ollama.client import MCPClient
from mcp_client_for_ollama.models.manager import ModelManager


def _make_manager(models):
    """Build a ModelManager with a fake ollama client returning the given models."""
    fake_ollama = AsyncMock()
    fake_ollama.list = AsyncMock(return_value={"models": models})
    return ModelManager(console=Console(), default_model="placeholder:1b", ollama=fake_ollama)


class TestResolveInitialModel(unittest.IsolatedAsyncioTestCase):
    async def test_no_models_installed_and_nothing_requested(self):
        mgr = _make_manager([])
        status = await mgr.resolve_initial_model(explicit_model=None, saved_model=None)
        self.assertEqual(status, "no-models")
        self.assertEqual(mgr.model, "")

    async def test_no_models_installed_keeps_explicit_request_visible(self):
        mgr = _make_manager([])
        status = await mgr.resolve_initial_model(explicit_model="llama3.2:3b", saved_model=None)
        self.assertEqual(status, "no-models")
        self.assertEqual(mgr.model, "llama3.2:3b")

    async def test_no_models_installed_keeps_saved_request_visible(self):
        mgr = _make_manager([])
        status = await mgr.resolve_initial_model(explicit_model=None, saved_model="llama3.2:3b")
        self.assertEqual(status, "no-models")
        self.assertEqual(mgr.model, "llama3.2:3b")

    async def test_explicit_model_installed_is_used_silently(self):
        mgr = _make_manager([{"model": "llama3.2:3b"}, {"model": "qwen2.5:7b"}])
        status = await mgr.resolve_initial_model(explicit_model="qwen2.5:7b", saved_model="llama3.2:3b")
        self.assertIsNone(status)
        self.assertEqual(mgr.model, "qwen2.5:7b")

    async def test_explicit_model_unavailable_falls_back_to_saved(self):
        mgr = _make_manager([{"model": "llama3.2:3b"}, {"model": "qwen2.5:7b"}])
        status = await mgr.resolve_initial_model(explicit_model="missing:1b", saved_model="llama3.2:3b")
        self.assertEqual(status, ("missing:1b", "llama3.2:3b"))
        self.assertEqual(mgr.model, "llama3.2:3b")

    async def test_explicit_model_unavailable_falls_back_to_first_when_no_saved(self):
        mgr = _make_manager([{"model": "zeta:1b"}, {"model": "alpha:1b"}])
        status = await mgr.resolve_initial_model(explicit_model="missing:1b", saved_model=None)
        self.assertEqual(status, ("missing:1b", "alpha:1b"))
        self.assertEqual(mgr.model, "alpha:1b")

    async def test_explicit_and_saved_both_unavailable_falls_back_to_first(self):
        mgr = _make_manager([{"model": "zeta:1b"}, {"model": "alpha:1b"}])
        status = await mgr.resolve_initial_model(explicit_model="missing:1b", saved_model="also-missing:1b")
        self.assertEqual(status, ("missing:1b", "alpha:1b"))
        self.assertEqual(mgr.model, "alpha:1b")

    async def test_saved_model_installed_is_used_silently(self):
        mgr = _make_manager([{"model": "llama3.2:3b"}, {"model": "qwen2.5:7b"}])
        status = await mgr.resolve_initial_model(explicit_model=None, saved_model="qwen2.5:7b")
        self.assertIsNone(status)
        self.assertEqual(mgr.model, "qwen2.5:7b")

    async def test_saved_model_unavailable_falls_back_to_first(self):
        mgr = _make_manager([{"model": "zeta:1b"}, {"model": "alpha:1b"}])
        status = await mgr.resolve_initial_model(explicit_model=None, saved_model="missing:1b")
        self.assertEqual(status, ("missing:1b", "alpha:1b"))
        self.assertEqual(mgr.model, "alpha:1b")

    async def test_auto_selects_first_alphabetically(self):
        mgr = _make_manager([{"model": "zeta:1b"}, {"model": "alpha:1b"}, {"model": "mid:1b"}])
        status = await mgr.resolve_initial_model(explicit_model=None, saved_model=None)
        self.assertEqual(status, "auto-selected")
        self.assertEqual(mgr.model, "alpha:1b")


class TestProcessQueryWithNoModel(unittest.IsolatedAsyncioTestCase):
    async def test_returns_early_without_calling_ollama(self):
        client = MCPClient()
        client.model_manager.set_model("")
        client.ollama.chat = AsyncMock(side_effect=AssertionError("ollama.chat should not be called"))

        response = await client.process_query("hi")

        self.assertEqual(response, "")
        client.ollama.chat.assert_not_called()


class TestPrintResolutionStatus(unittest.TestCase):
    def test_no_models_does_not_raise(self):
        ModelManager(console=Console()).print_resolution_status("no-models")

    def test_auto_selected_does_not_raise(self):
        mgr = ModelManager(console=Console())
        mgr.model = "alpha:1b"
        mgr.print_resolution_status("auto-selected")

    def test_none_is_noop(self):
        ModelManager(console=Console()).print_resolution_status(None)

    def test_fallback_tuple_does_not_raise(self):
        mgr = ModelManager(console=Console())
        mgr.model = "alpha:1b"
        mgr.print_resolution_status(("missing:1b", "alpha:1b"))


if __name__ == "__main__":
    unittest.main()
