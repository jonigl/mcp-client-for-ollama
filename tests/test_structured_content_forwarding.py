"""Regression tests for structured tool-result forwarding (#303).

MCP tools can return both `content` (human-oriented items) and
`structuredContent` (machine-oriented JSON). The LLM message must include
the structured data too, otherwise agent workflows that depend on it (e.g.
revision-guarded follow-up calls) cannot proceed.
"""

from mcp.types import CallToolResult, ImageContent, TextContent

from mcp_client_for_ollama.client import MCPClient


def _make_result(structured=None, items=None):
    return CallToolResult(
        content=items if items is not None else [
            TextContent(type="text", text="inspect_project completed. The complete result is available in structuredContent.")
        ],
        structuredContent=structured,
        isError=False,
    )


def test_structured_content_reaches_llm_message():
    """The text forwarded to the LLM must contain the structuredContent JSON."""
    structured = {
        "path": "C:\\apps\\shotcut-mcp\\ai-test.mlt",
        "revision": "947e191e72e5535a6620be650882450e7de7b17024fb4a504b259b4ddcd005cc",
    }
    tool_response, _images = MCPClient._extract_tool_response(_make_result(structured))
    assert "947e191e72e5535a6620be650882450e7de7b17024fb4a504b259b4ddcd005cc" in tool_response, (
        "structuredContent was not forwarded to the LLM (issue #303)"
    )
    assert "[Structured tool result]" in tool_response
    # plain text content is still forwarded unchanged
    assert "inspect_project completed" in tool_response


def test_plain_content_only_unchanged():
    """Without structuredContent the response is identical to the old behaviour."""
    tool_response, _images = MCPClient._extract_tool_response(_make_result(structured=None))
    assert "inspect_project completed" in tool_response
    assert "[Structured tool result]" not in tool_response


def test_structured_content_non_serializable():
    """Non-JSON-serializable structured payloads must not crash the loop."""
    class Weird:
        def __str__(self):
            return "<weird-object>"

    tool_response, _images = MCPClient._extract_tool_response(
        _make_result(structured={"weird": Weird()})
    )
    assert "[Structured tool result]" in tool_response
    assert "<weird-object>" in tool_response


def test_empty_content_with_structured_only():
    """Some tools return only structuredContent and no content items."""
    tool_response, _images = MCPClient._extract_tool_response(
        _make_result(structured={"ok": True}, items=[])
    )
    assert "[Structured tool result]" in tool_response
    assert '"ok": true' in tool_response


def test_image_collection_still_works():
    """The refactor must not break image extraction from content items."""
    image = ImageContent(type="image", data="aGVsbG8=", mimeType="image/png")
    tool_response, images = MCPClient._extract_tool_response(
        _make_result(items=[image]), has_vision=True
    )
    assert images == ["aGVsbG8="]
    assert "[Image: image/png, 8 bytes]" in tool_response


def test_snake_and_camel_case_attrs():
    """MCP SDK 2.x exposes structuredContent; older objects may use snake_case.

    The getter accepts both attribute spellings.
    """

    class CamelResult:
        content = [TextContent(type="text", text="done")]
        structuredContent = {"camel": True}

    class SnakeResult:
        content = [TextContent(type="text", text="done")]
        structured_content = {"snake": True}

    camel_response, _ = MCPClient._extract_tool_response(CamelResult())
    snake_response, _ = MCPClient._extract_tool_response(SnakeResult())
    assert '"camel": true' in camel_response
    assert '"snake": true' in snake_response
