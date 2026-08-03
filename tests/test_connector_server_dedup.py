"""Repro: two server entries that resolve to the same name silently collide.

`connect_to_servers` concatenates its five sources (registry mapping, scripts,
`-u` URLs, config file, Claude Desktop) into one list with no deduplication,
and `_connect_to_server` stores each result with a bare
`self.sessions[server_name] = ...`. When two entries share a name the second
overwrites the first, while the first server's tools stay behind in
`available_tools` pointing at a session that no longer exists.

Two ways this happens in practice:

1. The same server reached from the registry *and* from `-u` (issue #274:
   `unreal-mcp` and `127_0_0_1_8000` are one server, connected twice).
2. Two different servers on one host:port, because `process_server_urls`
   derives the name from `netloc` alone and ignores the path.

Same in-process-real-server approach as test_connector_e2e.py.
"""

import contextlib
import json
import threading
import unittest
from contextlib import AsyncExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rich.console import Console

from mcp_client_for_ollama.server.connector import ServerConnector


def _tool(name):
    return {"name": name, "description": name, "inputSchema": {"type": "object", "properties": {}}}


# Path -> tool exposed there. Both live on one host:port, which is the point.
TOOLS_BY_PATH = {"/alpha": _tool("alpha_tool"), "/beta": _tool("beta_tool")}


class _Handler(BaseHTTPRequestHandler):
    """Minimal Streamable HTTP MCP server whose tool list depends on the path."""

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

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            self._send_empty(400)
            return

        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:
            self._send_empty(202)  # notification
            return

        path = self.path.split("?")[0]

        if method == "initialize":
            self._result(msg_id, {
                "protocolVersion": msg["params"]["protocolVersion"],
                "capabilities": {"tools": {}},  # tools only: no resources/prompts round trips
                "serverInfo": {"name": f"fake{path}", "version": "1.0.0"},
            }, extra_headers={"mcp-session-id": f"session{path}"})

        elif method == "tools/list":
            self._result(msg_id, {"tools": [TOOLS_BY_PATH.get(path, _tool("default_tool"))]})

        else:
            self._send_json({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })

    def do_GET(self):
        self._send_empty(405)

    def do_DELETE(self):
        self._send_empty(200)


class TestServerEntryDeduplication(unittest.IsolatedAsyncioTestCase):
    """Real socket, real MCP SDK, real ServerConnector."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.server.daemon_threads = True
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    async def _connect(self, **kwargs):
        console = Console(record=True, width=200)
        stack = AsyncExitStack()
        connector = ServerConnector(stack, console=console)
        try:
            await connector.connect_to_servers(**kwargs)
            # Snapshot before teardown; the connector is unusable after aclose().
            return {
                "sessions": dict(connector.sessions),
                "tool_names": [t.name for t in connector.available_tools],
                "enabled": dict(connector.enabled_tools),
                "output": console.export_text(),
            }
        finally:
            with contextlib.suppress(BaseException):
                await stack.aclose()

    async def test_same_server_from_registry_and_url_flag_connects_once(self):
        """#274: `ollmcp -u <url>` for a server already in the registry.

        The registry entry and the `-u` entry are the same endpoint, so this
        must produce one connection and one copy of each tool -- not two.
        """
        url = self.url("/alpha")
        result = await self._connect(
            server_configs={"unreal-mcp": {"type": "streamable_http", "url": url}},
            server_urls=[url],
        )

        assert len(result["sessions"]) == 1, (
            "one endpoint reached from two sources must yield one session, got "
            f"{sorted(result['sessions'])}"
        )
        assert len(result["tool_names"]) == len(set(result["tool_names"])), (
            f"the same tool is offered to the model twice: {result['tool_names']}"
        )

    async def test_two_servers_on_one_host_port_keep_separate_sessions(self):
        """Names come from netloc only, so different paths collide.

        The second connection overwrites the first in `sessions`, but the first
        server's tools remain in `available_tools`, so they now resolve to a
        session that does not own them.
        """
        result = await self._connect(server_urls=[self.url("/alpha"), self.url("/beta")])

        assert len(result["sessions"]) == 2, (
            "two distinct servers must not share one session slot, got "
            f"{sorted(result['sessions'])}"
        )

        # Every advertised tool must be owned by the session it is namespaced to.
        for name in result["tool_names"]:
            server_name = name.rsplit(".", 1)[0]
            owned = [t.name for t in result["sessions"].get(server_name, {}).get("tools", [])]
            assert name in owned, (
                f"tool {name!r} is offered to the model but session "
                f"{server_name!r} does not own it (owns {owned}) -- calling it "
                "routes to the wrong server"
            )


if __name__ == "__main__":
    unittest.main()
