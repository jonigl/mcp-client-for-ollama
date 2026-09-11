"""Unset num_ctx must not become any-llm's 32000 default (issue #305)."""

from rich.console import Console

from any_llm.providers.ollama.ollama import OllamaProvider
from any_llm.types.completion import CompletionParams

from mcp_client_for_ollama.models.config_manager import ModelConfigManager


def _params() -> CompletionParams:
    return CompletionParams(
        model_id="qwen3:1.7b",
        messages=[{"role": "user", "content": "hi"}],
    )


def test_any_llm_still_defaults_missing_num_ctx_to_32000():
    """Document the upstream trap this workaround exists for."""
    converted = OllamaProvider._convert_completion_params(_params())
    assert converted["num_ctx"] == 32000


def test_unset_num_ctx_reaches_any_llm_as_none_not_32000():
    mgr = ModelConfigManager(console=Console())
    assert mgr.num_ctx is None
    kwargs = mgr.get_completion_kwargs("ollama")
    assert "num_ctx" in kwargs
    assert kwargs["num_ctx"] is None
    converted = OllamaProvider._convert_completion_params(_params(), **kwargs)
    assert converted["num_ctx"] is None


def test_explicit_num_ctx_still_passed_through_any_llm():
    mgr = ModelConfigManager(console=Console())
    mgr.num_ctx = 8192
    kwargs = mgr.get_completion_kwargs("ollama")
    assert kwargs["num_ctx"] == 8192
    converted = OllamaProvider._convert_completion_params(_params(), **kwargs)
    assert converted["num_ctx"] == 8192


def test_non_ollama_provider_omits_num_ctx():
    mgr = ModelConfigManager(console=Console())
    mgr.num_ctx = 8192
    assert "num_ctx" not in mgr.get_completion_kwargs("openai")
