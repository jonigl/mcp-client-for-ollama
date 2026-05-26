"""Test resources functionality."""

import base64
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import AsyncExitStack

from mcp_client_for_ollama.server.connector import ServerConnector
from mcp_client_for_ollama.resources.manager import ResourceManager
from rich.console import Console


class TestResourceManager(unittest.TestCase):
    """Test ResourceManager class."""

    def setUp(self):
        self.console = Console()
        self.manager = ResourceManager(self.console)

    def test_initial_state(self):
        assert self.manager.resources_by_server == {}
        assert self.manager.templates_by_server == {}
        assert not any(self.manager.resources_by_server.values())
        assert not any(self.manager.templates_by_server.values())
        assert sum(len(r) for r in self.manager.resources_by_server.values()) == 0

    def test_set_resources(self):
        mock_resource = MagicMock()
        mock_resource.uri = "file:///test.txt"
        mock_resource.name = "test.txt"
        mock_resource.description = "Test file"
        mock_resource.mimeType = "text/plain"

        self.manager.set_resources({"test-server": [mock_resource]})

        assert any(self.manager.resources_by_server.values())
        assert sum(len(r) for r in self.manager.resources_by_server.values()) == 1

    def test_set_templates(self):
        mock_template = MagicMock()
        mock_template.uriTemplate = "file:///{path}"
        mock_template.name = "Project Files"
        mock_template.description = "Access project files"
        mock_template.mimeType = None

        self.manager.set_templates({"test-server": [mock_template]})

        assert any(self.manager.templates_by_server.values())
        templates = self.manager.list_all_templates()
        assert len(templates) == 1
        assert templates[0]['uriTemplate'] == "file:///{path}"
        assert templates[0]['name'] == "Project Files"

    def test_find_resource(self):
        mock_resource = MagicMock()
        mock_resource.uri = "file:///test.txt"
        mock_resource.name = "test.txt"

        self.manager.set_resources({"test-server": [mock_resource]})

        result = self.manager.find_resource("file:///test.txt")
        assert result is not None
        server_name, resource = result
        assert server_name == "test-server"
        assert resource.uri == "file:///test.txt"

    def test_find_resource_not_found(self):
        assert self.manager.find_resource("file:///nonexistent.txt") is None

    def test_list_all(self):
        for i, srv in enumerate(["server1", "server2"], 1):
            r = MagicMock()
            r.uri = f"file:///test{i}.txt"
            r.name = f"test{i}.txt"
            r.description = f"Test file {i}"
            r.mimeType = "text/plain"
            self.manager.set_resources({srv: [r]} if i == 1 else {**self.manager.resources_by_server, srv: [r]})

        resources = self.manager.list_all()
        assert len(resources) == 2

    def test_get_resources_by_server(self):
        mock_resource = MagicMock()
        mock_resource.uri = "file:///test.txt"
        mock_resource.name = "test.txt"
        mock_resource.description = "Test file"
        mock_resource.mimeType = "text/plain"

        self.manager.set_resources({"test-server": [mock_resource]})

        by_server = self.manager.resources_by_server
        assert "test-server" in by_server
        assert len(by_server["test-server"]) == 1
        assert str(by_server["test-server"][0].uri) == "file:///test.txt"

    def test_get_known_uris(self):
        mock_resource = MagicMock()
        mock_resource.uri = "file:///test.txt"
        mock_resource.name = "test.txt"

        mock_template = MagicMock()
        mock_template.uriTemplate = "file:///{path}"
        mock_template.name = "Project Files"

        self.manager.set_resources({"server1": [mock_resource]})
        self.manager.set_templates({"server1": [mock_template]})

        known = self.manager.get_known_uris()
        assert "file:///test.txt" in known
        assert "file:///{path}" in known

    def test_get_known_uris_empty(self):
        assert self.manager.get_known_uris() == set()


class TestResourceManagerMultiContent(unittest.IsolatedAsyncioTestCase):
    """Test ResourceHandler.read_resource content handling."""

    async def test_read_multi_content_resource(self):
        from mcp_client_for_ollama.resources.handler import ResourceHandler

        console = MagicMock()
        manager = ResourceManager(console)

        mock_resource = MagicMock()
        mock_resource.uri = "doc:///multi"
        mock_resource.name = "multi"
        manager.set_resources({"srv": [mock_resource]})

        handler = ResourceHandler(console, manager, MagicMock())

        # Build a read_result with two text content blocks
        block1 = MagicMock(spec=['text', 'mimeType'])
        block1.text = "Hello"
        block1.mimeType = 'text/plain'
        block2 = MagicMock(spec=['text', 'mimeType'])
        block2.text = "World"
        block2.mimeType = 'text/plain'

        mock_read_result = MagicMock()
        mock_read_result.contents = [block1, block2]

        mock_session = AsyncMock()
        mock_session.read_resource.return_value = mock_read_result

        sessions = {"srv": {"session": mock_session}}
        result = await handler.read_resource("doc:///multi", sessions)

        assert result is not None
        assert result.text == "Hello\nWorld"
        assert result.images == []

    async def test_read_resource_non_image_binary_skipped(self):
        """Non-image binary blobs (PDF, zip, etc.) are skipped and return None."""
        from mcp_client_for_ollama.resources.handler import ResourceHandler

        console = MagicMock()
        manager = ResourceManager(console)

        mock_resource = MagicMock()
        mock_resource.uri = "doc:///report.pdf"
        mock_resource.name = "report.pdf"
        manager.set_resources({"srv": [mock_resource]})

        handler = ResourceHandler(console, manager, MagicMock())

        blob_block = MagicMock(spec=['blob', 'mimeType'])
        blob_block.blob = b"%PDF-binary-data"
        blob_block.mimeType = 'application/pdf'  # non-image binary

        mock_read_result = MagicMock()
        mock_read_result.contents = [blob_block]

        mock_session = AsyncMock()
        mock_session.read_resource.return_value = mock_read_result

        sessions = {"srv": {"session": mock_session}}
        result = await handler.read_resource("doc:///report.pdf", sessions)

        assert result is None

    async def test_read_resource_image_blob_returned(self):
        """Image blobs are base64-encoded and returned in result.images."""
        from mcp_client_for_ollama.resources.handler import ResourceHandler

        console = MagicMock()
        manager = ResourceManager(console)

        mock_resource = MagicMock()
        mock_resource.uri = "img:///photo.png"
        mock_resource.name = "photo.png"
        manager.set_resources({"srv": [mock_resource]})

        handler = ResourceHandler(console, manager, MagicMock())

        raw_bytes = b"\x89PNG\r\nfakedata"
        blob_block = MagicMock(spec=['blob', 'mimeType'])
        blob_block.blob = raw_bytes
        blob_block.mimeType = 'image/png'

        mock_read_result = MagicMock()
        mock_read_result.contents = [blob_block]

        mock_session = AsyncMock()
        mock_session.read_resource.return_value = mock_read_result

        sessions = {"srv": {"session": mock_session}}
        result = await handler.read_resource("img:///photo.png", sessions)

        assert result is not None
        assert bool(result)  # ResourceResult.__bool__ True when images present
        assert result.text == ''
        assert len(result.images) == 1
        assert result.images[0] == base64.b64encode(raw_bytes).decode('ascii')

    async def test_read_resource_image_already_base64(self):
        """Image blobs that arrive as base64 strings are passed through unchanged."""
        from mcp_client_for_ollama.resources.handler import ResourceHandler

        console = MagicMock()
        manager = ResourceManager(console)

        mock_resource = MagicMock()
        mock_resource.uri = "img:///logo.png"
        mock_resource.name = "logo.png"
        manager.set_resources({"srv": [mock_resource]})

        handler = ResourceHandler(console, manager, MagicMock())

        b64_string = base64.b64encode(b"fakepng").decode('ascii')
        blob_block = MagicMock(spec=['blob', 'mimeType'])
        blob_block.blob = b64_string  # already a string
        blob_block.mimeType = 'image/png'

        mock_read_result = MagicMock()
        mock_read_result.contents = [blob_block]

        mock_session = AsyncMock()
        mock_session.read_resource.return_value = mock_read_result

        sessions = {"srv": {"session": mock_session}}
        result = await handler.read_resource("img:///logo.png", sessions)

        assert result is not None
        assert result.images == [b64_string]


class TestResourceCapability(unittest.IsolatedAsyncioTestCase):
    """Test resource and template capability detection in ServerConnector."""

    async def test_server_with_resources_and_templates(self):
        """Resources and templates are both fetched when server supports them."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            server = {"name": "test-server", "type": "script", "path": "/tmp/test_server.py"}

            mock_session = AsyncMock()
            mock_init_result = MagicMock()
            mock_init_result.capabilities = MagicMock()
            mock_init_result.capabilities.tools = None
            mock_init_result.capabilities.prompts = None
            mock_init_result.capabilities.resources = MagicMock()

            mock_resource = MagicMock()
            mock_resource.uri = "file:///test.txt"
            mock_resource.name = "test.txt"

            mock_template = MagicMock()
            mock_template.uriTemplate = "file:///{path}"
            mock_template.name = "Project Files"

            mock_resources_response = MagicMock()
            mock_resources_response.resources = [mock_resource]

            mock_templates_response = MagicMock()
            mock_templates_response.resourceTemplates = [mock_template]

            mock_session.initialize.return_value = mock_init_result
            mock_session.list_resources.return_value = mock_resources_response
            mock_session.list_resource_templates.return_value = mock_templates_response

            with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
                 patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
                 patch.object(connector, '_create_script_params', return_value=MagicMock()):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock()

                result = await connector._connect_to_server(server)

                assert result is True
                assert "test-server" in connector.resources_by_server
                assert connector.resources_by_server["test-server"][0].uri == "file:///test.txt"
                assert "test-server" in connector.templates_by_server
                assert connector.templates_by_server["test-server"][0].uriTemplate == "file:///{path}"
                mock_session.list_resources.assert_called_once()
                mock_session.list_resource_templates.assert_called_once()

    async def test_server_without_resources_capability(self):
        """No resources or templates fetched when server lacks the capability."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            server = {"name": "test-server", "type": "script", "path": "/tmp/test_server.py"}

            mock_session = AsyncMock()
            mock_init_result = MagicMock()
            mock_init_result.capabilities = MagicMock()
            mock_init_result.capabilities.tools = None
            mock_init_result.capabilities.prompts = None
            mock_init_result.capabilities.resources = None

            mock_session.initialize.return_value = mock_init_result

            with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
                 patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
                 patch.object(connector, '_create_script_params', return_value=MagicMock()):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock()

                result = await connector._connect_to_server(server)

                assert result is True
                assert "test-server" not in connector.resources_by_server
                assert "test-server" not in connector.templates_by_server
                mock_session.list_resources.assert_not_called()
                mock_session.list_resource_templates.assert_not_called()


if __name__ == '__main__':
    unittest.main()
