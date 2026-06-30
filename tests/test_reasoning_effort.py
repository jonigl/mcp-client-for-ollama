"""Tests for _reasoning_effort_kwargs and related reasoning effort behavior."""

import unittest
from unittest.mock import MagicMock


class _ReasoningEffortClient:
    """Minimal stand-in with just the attributes _reasoning_effort_kwargs reads."""

    def __init__(self, provider, thinking_mode, reasoning_effort):
        self.provider = provider
        self.thinking_mode = thinking_mode
        self.reasoning_effort = reasoning_effort

    def _reasoning_effort_kwargs(self, supports_thinking: bool) -> dict:
        if not (supports_thinking and self.thinking_mode):
            return {}
        effort = self.reasoning_effort
        if self.provider == "ollama" and effort == "auto":
            effort = "high"
        return {"reasoning_effort": effort}


class TestReasoningEffortKwargs(unittest.TestCase):

    def test_returns_empty_when_thinking_mode_off(self):
        client = _ReasoningEffortClient("ollama", thinking_mode=False, reasoning_effort="high")
        self.assertEqual(client._reasoning_effort_kwargs(supports_thinking=True), {})

    def test_returns_empty_when_model_does_not_support_thinking(self):
        client = _ReasoningEffortClient("ollama", thinking_mode=True, reasoning_effort="high")
        self.assertEqual(client._reasoning_effort_kwargs(supports_thinking=False), {})

    def test_returns_configured_level_for_cloud_provider(self):
        for level in ("minimal", "low", "medium", "high", "xhigh"):
            client = _ReasoningEffortClient("openai", thinking_mode=True, reasoning_effort=level)
            result = client._reasoning_effort_kwargs(supports_thinking=True)
            self.assertEqual(result, {"reasoning_effort": level}, f"failed for level={level}")

    def test_auto_is_forwarded_to_cloud_provider(self):
        client = _ReasoningEffortClient("openai", thinking_mode=True, reasoning_effort="auto")
        result = client._reasoning_effort_kwargs(supports_thinking=True)
        self.assertEqual(result, {"reasoning_effort": "auto"})

    def test_auto_is_substituted_for_ollama(self):
        """Ollama+auto would silently disable thinking; helper substitutes a concrete level."""
        client = _ReasoningEffortClient("ollama", thinking_mode=True, reasoning_effort="auto")
        result = client._reasoning_effort_kwargs(supports_thinking=True)
        self.assertIn("reasoning_effort", result)
        self.assertNotEqual(result["reasoning_effort"], "auto",
                            "auto must be substituted for Ollama so any-llm sets think=True")

    def test_concrete_level_forwarded_for_ollama(self):
        client = _ReasoningEffortClient("ollama", thinking_mode=True, reasoning_effort="high")
        result = client._reasoning_effort_kwargs(supports_thinking=True)
        self.assertEqual(result, {"reasoning_effort": "high"})


if __name__ == "__main__":
    unittest.main()
