"""Test server connector functionality."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from rich.console import Console
from mcp_client_for_ollama.server.connector import ServerConnector
from mcp_client_for_ollama.utils.constants import MCP_PROTOCOL_VERSION
from contextlib import AsyncExitStack


def test_get_headers_from_server_sse():
    """Test that headers are correctly extracted and formatted for SSE servers."""
    connector = ServerConnector(AsyncExitStack())

    # Test SSE server with no custom headers
    server = {
        "name": "test-sse",
        "type": "sse",
        "url": "http://localhost:8000/sse"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_streamable_http():
    """Test that headers are correctly extracted and formatted for Streamable HTTP servers."""
    connector = ServerConnector(AsyncExitStack())

    # Test Streamable HTTP server with no custom headers
    server = {
        "name": "test-http",
        "type": "streamable_http",
        "url": "http://localhost:8000/mcp"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_with_custom_headers():
    """Test that custom headers are normalized to lowercase and protocol header is added."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with custom headers (mixed case)
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value"
        }
    }

    headers = connector._get_headers_from_server(server)

    # Verify custom headers are normalized to lowercase
    assert headers["authorization"] == "Bearer token123"
    assert headers["x-custom-header"] == "custom-value"

    # Verify uppercase keys don't exist
    assert "Authorization" not in headers
    assert "X-Custom-Header" not in headers

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION

    # Verify no uppercase version exists
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_from_server_with_config():
    """Test that headers are extracted from config subdict and normalized to lowercase."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with headers in config subdict
    server = {
        "name": "test-server",
        "type": "streamable_http",
        "config": {
            "url": "http://localhost:8000/mcp",
            "headers": {
                "X-API-Key": "secret-key"
            }
        }
    }

    headers = connector._get_headers_from_server(server)

    # Verify headers from config are normalized to lowercase
    assert headers["x-api-key"] == "secret-key"
    assert "X-API-Key" not in headers

    # Verify MCP Protocol Version header is added with lowercase key
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION


def test_get_headers_from_server_script_type():
    """Test that script-type servers don't get the MCP protocol header."""
    connector = ServerConnector(AsyncExitStack())

    # Test script server (should not add protocol header)
    server = {
        "name": "test-script",
        "type": "script",
        "path": "/path/to/server.py"
    }

    headers = connector._get_headers_from_server(server)

    # Verify MCP Protocol Version header is NOT added for script type
    assert "mcp-protocol-version" not in headers
    assert "MCP-Protocol-Version" not in headers


def test_get_headers_no_duplicate_protocol_version():
    """Test that we don't create duplicate protocol version headers and normalize to lowercase."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with uppercase protocol header in custom headers
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "MCP-Protocol-Version": "old-version",
            "Authorization": "Bearer token"
        }
    }

    headers = connector._get_headers_from_server(server)

    # All headers should be lowercase
    assert "mcp-protocol-version" in headers
    assert headers["mcp-protocol-version"] == MCP_PROTOCOL_VERSION
    assert headers["authorization"] == "Bearer token"

    # No uppercase headers should exist
    assert "MCP-Protocol-Version" not in headers
    assert "Authorization" not in headers


def test_header_case_normalization():
    """Test that headers with different cases get normalized and don't create duplicates."""
    connector = ServerConnector(AsyncExitStack())

    # Test server with headers in various cases
    server = {
        "name": "test-server",
        "type": "sse",
        "url": "http://localhost:8000/sse",
        "headers": {
            "Content-Type": "application/json",
            "content-type": "text/plain",  # This should overwrite the above
            "Authorization": "Bearer token1",
            "AUTHORIZATION": "Bearer token2",  # This should overwrite the above
        }
    }

    headers = connector._get_headers_from_server(server)

    # All headers should be lowercase and only one value per header name
    assert "content-type" in headers
    assert "Content-Type" not in headers
    assert "authorization" in headers
    assert "Authorization" not in headers
    assert "AUTHORIZATION" not in headers

    # Should have exactly 3 headers: content-type, authorization, mcp-protocol-version
    assert len(headers) == 3
    assert "mcp-protocol-version" in headers


def test_get_url_from_server():
    """Test URL extraction from server configuration."""
    connector = ServerConnector(AsyncExitStack())

    # Test URL directly in server dict
    server = {
        "name": "test-server",
        "url": "http://localhost:8000/sse"
    }
    assert connector._get_url_from_server(server) == "http://localhost:8000/sse"

    # Test URL in config subdict
    server = {
        "name": "test-server",
        "config": {
            "url": "http://localhost:9000/mcp"
        }
    }
    assert connector._get_url_from_server(server) == "http://localhost:9000/mcp"

    # Test no URL
    server = {
        "name": "test-server"
    }
    assert connector._get_url_from_server(server) is None


class TestCapabilityHandling(unittest.IsolatedAsyncioTestCase):
    """Test capability-based feature detection."""

    async def test_server_without_tools_capability(self):
        """Test that connection succeeds when server doesn't support tools."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            # Mock server configuration
            server = {
                "name": "test-server",
                "type": "script",
                "path": "/fake/path.py"
            }

            # Mock the session and initialization
            mock_session = AsyncMock()
            # __aenter__ yields this mock; falsy __aexit__ so it can't swallow assertions.
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = False
            mock_init_result = MagicMock()
            mock_init_result.capabilities = MagicMock()
            mock_init_result.capabilities.tools = None  # No tools capability
            mock_init_result.capabilities.prompts = None
            mock_session.initialize.return_value = mock_init_result

            # Mock the transport and session creation
            with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
                 patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
                 patch.object(connector, '_create_script_params', return_value=MagicMock()):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=False)

                # Connect to server
                result = await connector._connect_to_server(server)

                # Verify connection succeeded despite no tools
                assert result is True
                assert "test-server" in connector.sessions
                assert connector.sessions["test-server"]["tools"] == []
                assert mock_session.list_tools.call_count == 0  # Should not call list_tools

    async def test_server_without_prompts_capability(self):
        """Test that connection succeeds when server doesn't support prompts."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            # Mock server configuration
            server = {
                "name": "test-server",
                "type": "script",
                "path": "/fake/path.py"
            }

            # Mock the session and initialization
            mock_session = AsyncMock()
            # __aenter__ yields this mock; falsy __aexit__ so it can't swallow assertions.
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = False
            mock_init_result = MagicMock()
            mock_init_result.capabilities = MagicMock()
            mock_init_result.capabilities.tools = MagicMock()  # Has tools
            mock_init_result.capabilities.prompts = None  # No prompts capability

            # Mock list_tools response
            mock_tools_response = MagicMock()
            mock_tools_response.tools = []
            mock_session.initialize.return_value = mock_init_result
            mock_session.list_tools.return_value = mock_tools_response

            # Mock the transport and session creation
            with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
                 patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
                 patch.object(connector, '_create_script_params', return_value=MagicMock()):

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=False)

                # Connect to server
                result = await connector._connect_to_server(server)

                # Verify connection succeeded and prompts were not queried
                assert result is True
                assert "test-server" in connector.sessions
                assert "test-server" not in connector.prompts_by_server
                assert mock_session.list_prompts.call_count == 0  # Should not call list_prompts

    async def test_server_with_all_capabilities(self):
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            # Mock server configuration
            server = {
                "name": "test-server",
                "type": "script",
                "path": "/fake/path.py"
            }

            # Mock the session and initialization
            mock_session = AsyncMock()
            # __aenter__ yields this mock; falsy __aexit__ so it can't swallow assertions.
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = False
            mock_init_result = MagicMock()
            mock_init_result.capabilities = MagicMock()
            mock_init_result.capabilities.tools = MagicMock()  # Has tools
            mock_init_result.capabilities.prompts = MagicMock()  # Has prompts
            mock_init_result.capabilities.resources = MagicMock()  # Has resources (not used yet)

            # Mock list_tools response
            mock_tool = MagicMock()
            mock_tool.name = "test_tool"
            mock_tool.description = "A test tool"
            mock_tool.inputSchema = {}
            mock_tools_response = MagicMock()
            mock_tools_response.tools = [mock_tool]
            mock_session.list_tools.return_value = mock_tools_response

            # Mock list_prompts response
            mock_prompt = MagicMock()
            mock_prompt.name = "test_prompt"
            mock_prompts_response = MagicMock()
            mock_prompts_response.prompts = [mock_prompt]
            mock_session.list_prompts.return_value = mock_prompts_response

            mock_session.initialize.return_value = mock_init_result

            # Mock the transport and session creation
            with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
                 patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
                 patch.object(connector, '_create_script_params', return_value=MagicMock()), \
                 patch('mcp_client_for_ollama.server.connector.Tool') as mock_tool_class:

                # Make Tool constructor return the mock tool with proper attributes
                mock_tool_class.return_value = mock_tool

                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=False)

                # Connect to server
                result = await connector._connect_to_server(server)

                # Verify connection succeeded and both tools and prompts were listed
                assert result is True
                assert "test-server" in connector.sessions
                assert len(connector.sessions["test-server"]["tools"]) == 1
                assert "test-server" in connector.prompts_by_server
                assert len(connector.prompts_by_server["test-server"]) == 1
                assert mock_session.list_tools.call_count == 1
                assert mock_session.list_tools.call_count == 1
            assert mock_session.list_prompts.call_count == 1


class TestConnectToServersMerging(unittest.IsolatedAsyncioTestCase):
    """Test that connect_to_servers parses and merges the server_configs mapping
    (the registry's merged scopes) together with other server sources."""

    async def test_server_configs_mapping_connects_each_entry(self):
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            with patch.object(connector, '_connect_to_server', new=AsyncMock(return_value=True)) as mock_connect:
                await connector.connect_to_servers(
                    server_configs={
                        "fs": {"command": "npx", "args": ["-y", "server-fs"]},
                        "weather": {"command": "python", "args": ["weather.py"]},
                    }
                )

            connected_names = {call.args[0]["name"] for call in mock_connect.call_args_list}
            assert connected_names == {"fs", "weather"}

    async def test_server_configs_merges_with_server_paths(self):
        """A registry-provided server_configs entry and a --mcp-server path should
        both be connected, not just one (sources are additive, not exclusive)."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            with patch.object(connector, '_connect_to_server', new=AsyncMock(return_value=True)) as mock_connect:
                await connector.connect_to_servers(
                    server_configs={"fs": {"command": "npx", "args": ["-y", "server-fs"]}},
                    server_paths=[__file__],
                )

            connected_names = {call.args[0]["name"] for call in mock_connect.call_args_list}
            assert connected_names == {"fs", os.path.basename(__file__).split('.')[0]}


class TestStreamableHttpNotPrefiltered(unittest.IsolatedAsyncioTestCase):
    """HTTP servers must reach _connect_to_server instead of being dropped by a
    pre-flight probe (#278)."""

    async def test_streamable_http_server_reaches_handshake(self):
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)

            with patch.object(connector, '_connect_to_server', new=AsyncMock(return_value=True)) as mock_connect:
                await connector.connect_to_servers(
                    server_urls=["https://mcp.unreachable.invalid/api/v1/connect"],
                )

            attempted = [call.args[0] for call in mock_connect.call_args_list]
            assert len(attempted) == 1, "the HTTP server must not be skipped"
            assert attempted[0]["type"] == "streamable_http"
            assert attempted[0]["url"] == "https://mcp.unreachable.invalid/api/v1/connect"


HANDSHAKE_ERROR = "did not respond to MCP initialization"


class TestPostInitCancellation(unittest.IsolatedAsyncioTestCase):
    """A cancellation raised after the handshake must not be reported as the
    server failing to answer initialize, and must not abort the connection (#274)."""

    def _mock_session(self, *, tools=True, prompts=False, resources=True):
        """Build a session mock whose capabilities match a server's advertisement."""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = False

        mock_init_result = MagicMock()
        mock_init_result.capabilities = MagicMock()
        mock_init_result.capabilities.tools = MagicMock() if tools else None
        mock_init_result.capabilities.prompts = MagicMock() if prompts else None
        mock_init_result.capabilities.resources = MagicMock() if resources else None
        mock_session.initialize.return_value = mock_init_result

        mock_tool = MagicMock()
        mock_tool.name = "spawn_actor"
        mock_tool.description = "Spawn an actor"
        mock_tool.inputSchema = {}
        mock_tool.outputSchema = None
        mock_tools_response = MagicMock()
        mock_tools_response.tools = [mock_tool]
        mock_session.list_tools.return_value = mock_tools_response

        return mock_session

    async def _connect(self, connector, mock_session):
        """Run a stdio connection against the given session mock."""
        server = {"name": "unreal-mcp", "type": "script", "path": "/fake/path.py"}
        with patch('mcp_client_for_ollama.server.connector.stdio_client') as mock_stdio, \
             patch('mcp_client_for_ollama.server.connector.ClientSession', return_value=mock_session), \
             patch.object(connector, '_create_script_params', return_value=MagicMock()):

            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=False)

            return await connector._connect_to_server(server)

    async def test_cancelled_resources_listing_keeps_the_connection(self):
        """A server that advertises resources but drops the stream on
        resources/list still connects, keeping the tools it already returned."""
        # Wide console so rich does not wrap the message being asserted on.
        console = Console(record=True, width=200)
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack, console=console)
            mock_session = self._mock_session()
            mock_session.list_resources.side_effect = asyncio.CancelledError()

            result = await self._connect(connector, mock_session)

        output = console.export_text()
        assert result is True, "one broken capability query must not fail the connection"
        assert "unreal-mcp" in connector.sessions
        assert [t.name for t in connector.available_tools] == ["unreal-mcp.spawn_actor"]
        assert HANDSHAKE_ERROR not in output, "initialize succeeded; do not blame the URL"

    async def test_cancellation_during_initialize_reports_handshake_failure(self):
        """The original message is still used when initialize itself is cancelled."""
        console = Console(record=True, width=200)
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack, console=console)
            mock_session = self._mock_session()
            mock_session.initialize.side_effect = asyncio.CancelledError()

            result = await self._connect(connector, mock_session)

        assert result is False
        assert HANDSHAKE_ERROR in console.export_text()
        assert connector.sessions == {}

    async def test_cancellation_after_initialize_is_not_reported_as_handshake_failure(self):
        """A cancellation once the handshake is done gets its own message."""
        console = Console(record=True, width=200)
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack, console=console)
            mock_session = self._mock_session()

            # Cancel while handing the transport over to the long-lived exit stack,
            # i.e. after initialize() has already returned.
            with patch.object(connector.exit_stack, 'enter_async_context',
                              side_effect=asyncio.CancelledError()):
                result = await self._connect(connector, mock_session)

        output = console.export_text()
        assert result is False
        assert HANDSHAKE_ERROR not in output
        assert "after a successful MCP initialization" in output

    async def test_failed_connection_discards_partial_state(self):
        """State registered before the failure must not survive it, otherwise the
        client keeps offering tools for a server it reported as unreachable."""
        async with AsyncExitStack() as stack:
            connector = ServerConnector(stack)
            mock_session = self._mock_session()

            # A malformed resources payload: truthy, but len() raises when the
            # summary line is built, after tools were already registered.
            class MalformedResources:
                def __bool__(self):
                    return True

            mock_resources_response = MagicMock()
            mock_resources_response.resources = MalformedResources()
            mock_session.list_resources.return_value = mock_resources_response

            result = await self._connect(connector, mock_session)

        assert result is False
        assert connector.sessions == {}
        assert connector.available_tools == []
        assert connector.enabled_tools == {}
        assert connector.resources_by_server == {}
