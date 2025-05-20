"""Version handling utilities for MCP Client for Ollama."""

import re
import json
import urllib.request
from mcp_client_for_ollama import __version__
from .constants import PYPI_PACKAGE_URL

def check_for_updates():
    """Check if a newer version of the package is available on PyPI.
    
    Returns:
        Tuple[bool, str, str]: (update_available, current_version, latest_version)
    """
    current_version = __version__

    try:
        with urllib.request.urlopen(PYPI_PACKAGE_URL, timeout=5) as response:
            data = json.load(response)
            latest_version = data.get("info", {}).get("version", current_version)

            # Compare versions (treating them as tuples of integers)
            def parse_version(version_str):
                # Extract numbers from version string (handles formats like 0.1.11)
                return tuple(map(int, re.findall(r'\d+', version_str)))

            current_parsed = parse_version(current_version)
            latest_parsed = parse_version(latest_version)

            update_available = latest_parsed > current_parsed
            return update_available, current_version, latest_version

    except Exception:
        # Return no update available on error
        return False, current_version, current_version
