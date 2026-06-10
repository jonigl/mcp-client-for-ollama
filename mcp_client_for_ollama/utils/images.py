"""Image format conversion for LLM provider compatibility."""

from typing import Any, Dict, List


def apply_images(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Ollama-style `images` fields to OpenAI content arrays.

    All any-llm providers expect the OpenAI content-array format for images.
    Providers that use a different native format (e.g. Ollama) convert
    internally from this universal representation.
    """
    result = []
    for msg in messages:
        if msg.get("images") and msg.get("role") == "user":
            content_parts = [{"type": "text", "text": msg.get("content", "")}]
            for img in msg["images"]:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                })
            new_msg = {k: v for k, v in msg.items() if k not in ("images", "content")}
            new_msg["content"] = content_parts
            result.append(new_msg)
        else:
            result.append(msg)
    return result
