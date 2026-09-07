"""Regression tests for structured tool-result forwarding (#303).

An MCP tool result carries human-oriented items in `content` and, optionally, a
machine-oriented JSON payload in `structuredContent`. The spec has a server that
returns structured content ALSO serialize it into a TextContent block, but only
"for backwards compatibility" -- a SHOULD, not a MUST. A conforming server may
therefore answer with `structuredContent` and no text at all, and that result
used to reach the model as "no text content returned".

So the payload is forwarded exactly when the server sent no text of its own.
When it did, that text is what the model gets: the two fields carry the same
information by construction, and SEP-1624 asks clients not to forward both.
"""

import json

from mcp.types import AudioContent, CallToolResult, ImageContent, TextContent

from mcp_client_for_ollama.client import MCPClient

client = MCPClient()


def _make_result(structured=None, items=None):
    return CallToolResult(
        content=items if items is not None else [
            TextContent(type="text", text="inspect_project completed.")
        ],
        structuredContent=structured,
        isError=False,
    )


def test_structured_content_reaches_llm_when_there_is_no_text():
    """The case the spec allows and we used to drop on the floor (#303)."""
    structured = {
        "path": "C:\\apps\\shotcut-mcp\\ai-test.mlt",
        "revision": "947e191e72e5535a6620be650882450e7de7b17024fb4a504b259b4ddcd005cc",
    }
    tool_response, _images = client._extract_tool_response(
        _make_result(structured=structured, items=[])
    )
    assert json.loads(tool_response) == structured


def test_no_content_and_no_structured_content():
    """An empty result still says something to the model."""
    tool_response, images = client._extract_tool_response(
        _make_result(structured=None, items=[])
    )
    assert tool_response == "Tool executed successfully (no text content returned)"
    assert images == []


def test_text_content_is_forwarded_alone():
    """A server that sent text gets that text forwarded, and only that: both
    fields hold the same information, so adding the payload would spend the
    model's context on it twice (SEP-1624)."""
    structured = {"temperature": 22.5, "conditions": "Partly cloudy"}
    tool_response, _images = client._extract_tool_response(
        _make_result(structured=structured, items=[
            TextContent(type="text", text=json.dumps(structured)),
        ])
    )
    assert tool_response == json.dumps(structured)


def test_text_content_wins_whatever_shape_it_has():
    """Including the shapes the reference SDKs actually emit: the serialized
    payload, a bare value, or one block per list item."""
    for label, structured, items, expected in [
        (
            "bare value next to the SDK's {'result': ...} wrapper",
            {"result": "line one\nline two"},
            [TextContent(type="text", text="line one\nline two")],
            "line one\nline two",
        ),
        (
            "one text block per list item",
            {"result": ["uno", "dos"]},
            [TextContent(type="text", text="uno"), TextContent(type="text", text="dos")],
            "uno\n\ndos",
        ),
    ]:
        tool_response, _images = client._extract_tool_response(
            _make_result(structured=structured, items=items)
        )
        assert tool_response == expected, f"{label}: {tool_response!r}"


def test_plain_content_only_unchanged():
    """Without structuredContent nothing changes."""
    tool_response, _images = client._extract_tool_response(_make_result(structured=None))
    assert tool_response == "inspect_project completed."


def test_forwarded_payload_is_compact():
    """The copy is ours, so it is serialized without indentation the model gains
    nothing from."""
    tool_response, _images = client._extract_tool_response(
        _make_result(structured={"a": 1, "b": [1, 2]}, items=[])
    )
    assert tool_response == '{"a":1,"b":[1,2]}'


def test_non_ascii_payload_is_not_escaped():
    r"""Escaping non-ASCII to \uXXXX bloats the payload (~6 chars per CJK
    character) and small local models echo the escapes back."""
    structured = {"city": "北京", "note": "café"}
    tool_response, _images = client._extract_tool_response(
        _make_result(structured=structured, items=[])
    )
    assert tool_response == '{"city":"北京","note":"café"}'
    assert json.loads(tool_response) == structured


def test_structured_content_non_serializable():
    """Payloads json.dumps cannot encode fall back to str() per value."""
    class Weird:
        def __str__(self):
            return "<weird-object>"

    tool_response, _images = client._extract_tool_response(
        _make_result(structured={"weird": Weird()}, items=[])
    )
    assert "<weird-object>" in tool_response


def test_payload_survives_next_to_media_only_content():
    """Image and audio placeholders are ours, not the server's text, so a tool
    answering with media plus a payload still forwards the payload."""
    items = [
        ImageContent(type="image", data="aGVsbG8=", mimeType="image/png"),
        AudioContent(type="audio", data="YXVkaW8=", mimeType="audio/wav"),
    ]
    tool_response, images = client._extract_tool_response(
        _make_result(structured={"ok": True}, items=items), has_vision=True
    )
    assert images == ["aGVsbG8="]
    assert "[Image: image/png, 8 bytes]" in tool_response
    assert tool_response.endswith('{"ok":true}')


def test_image_collection_still_works():
    """The extraction refactor must not break image handling."""
    image = ImageContent(type="image", data="aGVsbG8=", mimeType="image/png")
    tool_response, images = client._extract_tool_response(
        _make_result(items=[image]), has_vision=True
    )
    assert images == ["aGVsbG8="]
    assert "[Image: image/png, 8 bytes]" in tool_response
