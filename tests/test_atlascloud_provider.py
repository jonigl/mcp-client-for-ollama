"""Tests for the Atlas Cloud provider adapter."""

import json

from mcp_client_for_ollama.providers import (
    AtlasCloudAsyncClient,
    build_llm_client,
    is_atlascloud_host,
)


def test_is_atlascloud_host_detects_known_domain():
    assert is_atlascloud_host("https://api.atlascloud.ai/v1")
    assert is_atlascloud_host("https://www.atlascloud.ai")
    assert not is_atlascloud_host("http://localhost:11434")


def test_build_llm_client_uses_atlascloud_for_atlas_host():
    client = build_llm_client("https://api.atlascloud.ai/v1")

    assert isinstance(client, AtlasCloudAsyncClient)


def test_finalize_tool_calls_merges_streaming_arguments():
    client = AtlasCloudAsyncClient()
    parts = {}

    client._merge_tool_call_delta(parts, [
        {
            "index": 0,
            "id": "call_1",
            "function": {"name": "math.add", "arguments": "{\"a\":"},
        }
    ])
    client._merge_tool_call_delta(parts, [
        {
            "index": 0,
            "function": {"arguments": "1,\"b\":2}"},
        }
    ])

    tool_calls = client._finalize_tool_calls(parts)

    assert len(tool_calls) == 1
    assert tool_calls[0].id == "call_1"
    assert tool_calls[0].function.name == "math.add"
    assert tool_calls[0].function.arguments == {"a": 1, "b": 2}


def test_convert_messages_keeps_tool_call_id_for_tool_messages():
    client = AtlasCloudAsyncClient()

    messages = client._convert_messages([
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                type(
                    "ToolCall",
                    (),
                    {
                        "id": "call_123",
                        "function": type(
                            "Function",
                            (),
                            {"name": "echo.say", "arguments": {"text": "hello"}},
                        )(),
                    },
                )()
            ],
        },
        {
            "role": "tool",
            "content": "hello",
            "tool_name": "echo.say",
            "tool_call_id": "call_123",
        },
    ])

    assert messages[0]["tool_calls"][0]["id"] == "call_123"
    assert json.loads(messages[0]["tool_calls"][0]["function"]["arguments"]) == {"text": "hello"}
    assert messages[1]["tool_call_id"] == "call_123"
