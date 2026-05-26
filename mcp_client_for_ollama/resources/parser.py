"""Resource reference parser for MCP client.

Pure functions with no dependencies on the rest of the codebase.
"""
import re
from typing import NamedTuple, Set, Tuple, List, Dict


class ResourceRef(NamedTuple):
    """A resource reference extracted from user input."""
    uri: str
    is_template: bool


# Matches @-prefixed tokens: @ followed by non-whitespace characters.
_AT_TOKEN_RE = re.compile(r'@(\S+)')

# A URI must start with a scheme: one or more letters/digits/+/-/. followed by ://.
_URI_SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')

# Finds {variable} placeholders inside a URI template.
_TEMPLATE_VAR_RE = re.compile(r'\{([^}]+)\}')

# Trailing punctuation that is unlikely to be part of a valid URI.
_TRAILING_PUNCT = '.,;:!?)'


def extract_resource_refs(
    input_text: str,
    known_uris: Set[str],
) -> Tuple[str, List[ResourceRef]]:
    """Extract @uri resource references from user input text.

    A ``@token`` is treated as a resource reference when either:
    - It exactly matches an entry in ``known_uris`` (static resources or
      template URI patterns registered by the ResourceManager), OR
    - It looks like a URI (starts with a scheme such as ``file://``).

    Tokens that do not meet either condition — e.g. ``@username`` or
    ``user@example.com`` — are left untouched in the returned clean text.

    Args:
        input_text: Raw user input that may contain ``@uri`` references.
        known_uris: Set of known resource URIs and template URI patterns.

    Returns:
        ``(clean_text, refs)`` where:
        - ``clean_text`` is the input with matched ``@uri`` tokens removed
          and extra whitespace collapsed.
        - ``refs`` is a list of :class:`ResourceRef` namedtuples in the
          order they appeared.
    """
    refs: List[ResourceRef] = []
    # Store (start, end) spans to remove, keyed by the exact matched text.
    spans_to_remove: List[Tuple[int, int]] = []

    for match in _AT_TOKEN_RE.finditer(input_text):
        raw_uri = match.group(1)

        # Strip common trailing punctuation that is unlikely to be part of a URI.
        uri = raw_uri.rstrip(_TRAILING_PUNCT)
        if not uri:
            continue

        is_resource = uri in known_uris or bool(_URI_SCHEME_RE.match(uri))
        if not is_resource:
            continue

        is_template = '{' in uri and '}' in uri
        refs.append(ResourceRef(uri=uri, is_template=is_template))

        # The span to remove is '@' + stripped uri (not the raw match if trailing
        # punct was stripped — we leave that punctuation in place).
        token_start = match.start()
        token_end = token_start + 1 + len(uri)  # 1 for the '@'
        spans_to_remove.append((token_start, token_end))

    if not spans_to_remove:
        return input_text, refs

    # Remove matched spans (reverse order preserves positions).
    clean_text = input_text
    for start, end in reversed(spans_to_remove):
        clean_text = clean_text[:start] + clean_text[end:]

    # Collapse multiple spaces and strip leading/trailing whitespace.
    clean_text = re.sub(r' {2,}', ' ', clean_text).strip()

    return clean_text, refs


def extract_template_variables(uri_template: str) -> List[str]:
    """Return the variable names found in a URI template.

    For example::

        extract_template_variables('file:///{path}')  -> ['path']
        extract_template_variables('db://{host}/{db}') -> ['host', 'db']

    Args:
        uri_template: A URI template string with ``{variable}`` placeholders.

    Returns:
        Ordered list of variable names.
    """
    return _TEMPLATE_VAR_RE.findall(uri_template)


def resolve_template(uri_template: str, variables: Dict[str, str]) -> str:
    """Substitute variable values into a URI template.

    Unknown variables in ``variables`` are silently ignored.
    Unresolved placeholders (variables present in the template but absent
    from ``variables``) are left as-is.

    Args:
        uri_template: A URI template string with ``{variable}`` placeholders.
        variables: Mapping of variable name to its value.

    Returns:
        Resolved URI string.
    """
    result = uri_template
    for key, value in variables.items():
        result = result.replace('{' + key + '}', value)
    return result
