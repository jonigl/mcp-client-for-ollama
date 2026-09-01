"""End-to-end tests for ServerConnector against a real Streamable HTTP server.

Everything else in the connector suite mocks ClientSession away. These tests
run the real MCP SDK over a real socket, which is what exposed #274: a server
that drops the stream on resources/list makes the pending request fail *after*
a successful handshake, and that used to be reported as the server never
answering initialize.

Round two of the same issue is here as well: dropping the stream cancels the
anyio scope the transport runs in, so *swallowing* that cancellation and
keeping the connection left the scope cancelled inside the client's own task,
which then died with "Cancelled via cancel scope ..." at the next await, long
after the connection had been reported as successful.

The server runs in-process on an ephemeral port, so nothing here depends on a
fixed port being free. Assertions target the observable outcome (does the
connection survive, are the tools usable) rather than the exception type the
SDK happens to raise, so they stay valid across mcp releases.
"""

import asyncio
import contextlib
import json
import socket
import threading
import unittest
from contextlib import AsyncExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rich.console import Console

from mcp_client_for_ollama.server.connector import ServerConnector

HANDSHAKE_ERROR = "did not respond to MCP initialization"

TOOL = {
    "name": "spawn_actor",
    "description": "Spawn an actor in the level",
    "inputSchema": {"type": "object", "properties": {}},
}


class _MCPTestServer(ThreadingHTTPServer):
    """HTTP server whose resources/list behavior is switched per test."""

    daemon_threads = True
    allow_reuse_address = True
    mode = "healthy"  # or "drop_on_resources" / "drop_on_templates"


class _Handler(BaseHTTPRequestHandler):
    """Minimal Streamable HTTP MCP server.

    Advertises tools and resources but not prompts, mirroring the server in
    the #274 report.
    """

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # keep pytest output clean

    def _send_json(self, payload, extra_headers=None):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _result(self, msg_id, result, extra_headers=None):
        self._send_json({"jsonrpc": "2.0", "id": msg_id, "result": result}, extra_headers)

    def _drop(self):
        """Die mid-request, the way the server in #274 does."""
        with contextlib.suppress(OSError):
            self.connection.shutdown(socket.SHUT_RDWR)
        self.connection.close()
        self.close_connection = True

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            self._send_empty(400)
            return

        method, msg_id = msg.get("method"), msg.get("id")

        # Notifications carry no id and get an empty 202.
        if msg_id is None:
            self._send_empty(202)
            return

        if method == "initialize":
            self._result(msg_id, {
                # Echo the client's version so this stays valid as the SDK moves on.
                "protocolVersion": msg["params"]["protocolVersion"],
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "fake-unreal-mcp", "version": "1.0.0"},
            }, extra_headers={"mcp-session-id": "fake-unreal-session"})

        elif method == "tools/list":
            self._result(msg_id, {"tools": [TOOL]})

        elif method == "resources/list":
            if self.server.mode == "drop_on_resources":
                # The #274 trigger: advertise resources, then die when asked.
                return self._drop()
            self._result(msg_id, {"resources": [
                {"uri": "file:///level.umap", "name": "level.umap"},
            ]})

        elif method == "resources/templates/list":
            if self.server.mode == "drop_on_templates":
                # What the reporter's server actually does: resources/list is
                # answered, the request right after it kills the connection.
                return self._drop()
            self._result(msg_id, {"resourceTemplates": []})

        else:
            self._send_json({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })

    def do_GET(self):
        self._send_empty(405)  # no server->client SSE stream in this fake

    def do_DELETE(self):
        self._send_empty(200)


class TestConnectorAgainstRealServer(unittest.IsolatedAsyncioTestCase):
    """Real socket, real MCP SDK, real ServerConnector."""

    @classmethod
    def setUpClass(cls):
        cls.server = _MCPTestServer(("127.0.0.1", 0), _Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/mcp"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    async def _connect(self, mode):
        """Connect to the fake server in the given mode.

        Returns (ok, connector, output, still_running): `still_running` is what
        catches a cancellation left behind by a dead transport - it is False
        when an ordinary await after the connection gets cancelled.
        """
        type(self).server.mode = mode
        console = Console(record=True, width=200)
        stack = AsyncExitStack()
        connector = ServerConnector(stack, console=console)
        still_running = False
        try:
            ok = await connector._connect_to_server({
                "name": "unreal-mcp", "type": "streamable_http", "url": self.url,
            })
            try:
                # The client does plenty of awaiting after connecting; a scope
                # left cancelled by the connection turns the first of them into
                # a CancelledError with nothing to blame it on.
                await asyncio.sleep(0)
                still_running = True
            except asyncio.CancelledError:
                still_running = False
        finally:
            # In drop mode the server hard-resets the socket, so unwinding the
            # transport raises on its way out. That teardown noise is not what
            # these tests are about.
            with contextlib.suppress(BaseException):
                await stack.aclose()
        return ok, connector, console.export_text(), still_running

    async def test_healthy_server_connects_with_tools_and_resources(self):
        """Sanity check on the fake server: a well-behaved one connects fully."""
        ok, connector, _, still_running = await self._connect("healthy")

        assert ok is True
        assert [t.name for t in connector.available_tools] == ["unreal-mcp.spawn_actor"]
        assert "unreal-mcp" in connector.resources_by_server
        assert still_running is True

    async def test_stream_dropped_on_resources_keeps_the_connection(self):
        """#274: losing the stream on resources/list must not undo a working
        connection, nor be blamed on the URL."""
        ok, connector, output, _ = await self._connect("drop_on_resources")

        assert ok is True, "a broken resources/list must not fail the connection"
        assert "unreal-mcp" in connector.sessions
        assert [t.name for t in connector.available_tools] == ["unreal-mcp.spawn_actor"]
        assert connector.enabled_tools == {"unreal-mcp.spawn_actor": True}
        assert HANDSHAKE_ERROR not in output, "initialize succeeded; do not blame the URL"

    async def test_dropped_listing_leaves_no_cancellation_behind(self):
        """#274 round two: the dead transport's cancelled scope must not be
        handed to the shared exit stack, where it cancels the client itself."""
        for mode in ("drop_on_resources", "drop_on_templates"):
            with self.subTest(mode=mode):
                ok, connector, output, still_running = await self._connect(mode)

                assert ok is True
                assert still_running is True, (
                    "the connection left a cancelled scope in the client's task"
                )
                assert [t.name for t in connector.available_tools] == ["unreal-mcp.spawn_actor"]

    async def test_retry_names_the_listing_that_closed_the_connection(self):
        """The user gets told which request the server died on, spelled the way
        it goes over the wire so it can be matched with a server-side log."""
        _, _, output, _ = await self._connect("drop_on_templates")

        assert "closed the connection on resources/templates/list" in output
        # The listing that did answer is still there.
        assert "1 resource(s)" in output

    async def test_dropped_listing_keeps_the_session_usable(self):
        """Reconnecting is only worth it if the surviving session works."""
        type(self).server.mode = "drop_on_templates"
        stack = AsyncExitStack()
        connector = ServerConnector(stack, console=Console(record=True, width=200))
        try:
            assert await connector._connect_to_server({
                "name": "unreal-mcp", "type": "streamable_http", "url": self.url,
            })
            live = await connector.sessions["unreal-mcp"]["session"].list_tools()
            assert [t.name for t in live.tools] == ["spawn_actor"]
        finally:
            with contextlib.suppress(BaseException):
                await stack.aclose()


if __name__ == "__main__":
    unittest.main()
