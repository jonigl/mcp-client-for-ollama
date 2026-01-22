"""Content filtering utilities for MCP prompts, keeping this feature only for text messages for now"""
from typing import List, Tuple, Any


def filter_prompt_messages(messages: List[Any]) -> Tuple[List[dict], List[str]]:
    """Filter prompt messages to keep only text content

    Args:
        messages: List of PromptMessage objects from MCP server

    Returns:
        Tuple of (filtered_messages, skipped_types):
            - filtered_messages: List of dicts with role and text content
            - skipped_types: List of skipped content type names
    """
    filtered_messages = []
    skipped_types = set()

    for message in messages:
        role = message.role
        content = message.content

        # Handle different content types
        content_type = getattr(content, 'type', None)

        if content_type == 'text':
            # Keep text content
            text = getattr(content, 'text', '')
            filtered_messages.append({
                'role': role,
                'content': text
            })
        elif content_type in ('image', 'audio'):
            # Skip multimedia content
            skipped_types.add(content_type)
        elif content_type == 'resource':
            # Skip embedded resources
            skipped_types.add('resource')
        else:
            # Unknown type - try to extract text if available
            text = getattr(content, 'text', None)
            if text:
                filtered_messages.append({
                    'role': role,
                    'content': text
                })
            else:
                skipped_types.add(content_type or 'unknown')

    return filtered_messages, sorted(list(skipped_types))
