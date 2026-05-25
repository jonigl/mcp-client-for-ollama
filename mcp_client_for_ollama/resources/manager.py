"""Manager for MCP resources"""
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console


class ResourceManager:
    """Manages MCP resources and resource templates from multiple servers"""

    def __init__(self, console: Console):
        self.console = console
        self.resources_by_server: Dict[str, List[Any]] = {}
        self.templates_by_server: Dict[str, List[Any]] = {}

    def set_resources(self, resources_by_server: Dict[str, List[Any]]):
        """Set available static resources from all servers"""
        self.resources_by_server = resources_by_server

    def set_templates(self, templates_by_server: Dict[str, List[Any]]):
        """Set available resource templates from all servers"""
        self.templates_by_server = templates_by_server

    def find_resource(self, uri: str) -> Optional[Tuple[str, Any]]:
        """Find a static resource by URI. Returns (server_name, resource) or None."""
        for server_name, resources in self.resources_by_server.items():
            for resource in resources:
                if str(resource.uri) == uri:
                    return (server_name, resource)
        return None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all static resources with metadata (used for FZF completions)"""
        resources = []
        for server_name, server_resources in self.resources_by_server.items():
            for resource in server_resources:
                resources.append({
                    'uri': str(resource.uri),
                    'name': resource.name,
                    'server': server_name,
                    'description': getattr(resource, 'description', None),
                    'mimeType': getattr(resource, 'mimeType', None),
                })
        return resources

    def list_all_templates(self) -> List[Dict[str, Any]]:
        """List all resource templates with metadata (used for FZF completions)"""
        templates = []
        for server_name, server_templates in self.templates_by_server.items():
            for template in server_templates:
                templates.append({
                    'uriTemplate': template.uriTemplate,
                    'name': template.name,
                    'server': server_name,
                    'description': getattr(template, 'description', None),
                    'mimeType': getattr(template, 'mimeType', None),
                })
        return templates

    def get_known_uris(self) -> set:
        """Return the set of all known resource URIs and template URI patterns.

        Used by the resource parser to distinguish @uri tokens that refer to
        MCP resources from plain @-words (e.g. email addresses or @usernames).
        Static resource URIs and template URI patterns are both included.
        """
        uris: set = set()
        for resources in self.resources_by_server.values():
            for resource in resources:
                uris.add(str(resource.uri))
        for templates in self.templates_by_server.values():
            for template in templates:
                uris.add(template.uriTemplate)
        return uris
