"""Utilities for prompt injection and processing"""
from typing import List, Dict, Tuple


def convert_prompt_messages_to_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Convert prompt messages to chat history format

    Args:
        messages: List of filtered messages with 'role' and 'content'

    Returns:
        List of chat history entries with 'query' and 'response' keys
    """
    history_entries = []
    pending_user_query = None

    for msg in messages:
        if msg['role'] == 'user':
            # If we have a pending user query, save it first with empty response
            if pending_user_query:
                history_entries.append({
                    'query': pending_user_query,
                    'response': ''
                })
            # Store this user message for pairing with next assistant response
            pending_user_query = msg['content']
        elif msg['role'] == 'assistant':
            # Pair with pending user query or create standalone entry
            if pending_user_query:
                history_entries.append({
                    'query': pending_user_query,
                    'response': msg['content']
                })
                pending_user_query = None
            else:
                # Assistant message without preceding user message
                history_entries.append({
                    'query': '[Context from prompt]',
                    'response': msg['content']
                })

    # If there's a remaining user query without a response, add it
    if pending_user_query:
        history_entries.append({
            'query': pending_user_query,
            'response': ''
        })

    return history_entries


def validate_prompt_confirmation(confirmation: str) -> Tuple[bool, bool]:
    """Validate user confirmation for prompt injection

    Args:
        confirmation: User input string

    Returns:
        Tuple of (should_proceed: bool, should_cancel: bool)
        - (True, False): User accepted (y/yes)
        - (False, True): User cancelled (n/no/q/quit/cancel)
        - (False, False): Invalid input, ask again
    """
    if confirmation is None:
        return False, True

    conf_lower = confirmation.lower().strip()

    if conf_lower in ['y', 'yes']:
        return True, False
    elif conf_lower in ['n', 'no', 'q', 'quit', 'cancel']:
        return False, True
    else:
        return False, False
