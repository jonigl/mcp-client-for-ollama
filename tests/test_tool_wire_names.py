"""Tests for the tool names ollmcp puts on the wire."""

import unittest

from mcp import Tool

from mcp_client_for_ollama.tools.manager import build_tool_payload, wire_name


def _tool(name):
    return Tool(name=name, description=f"desc for {name}", inputSchema={"type": "object"})


class TestWireName(unittest.TestCase):
    """Qualified names must survive a provider's function-name validation."""

    def test_dot_separator_is_replaced(self):
        # OpenAI and Anthropic both reject the dot in "<server>.<tool>".
        self.assertEqual(wire_name("playwright.browser_navigate"), "playwright_browser_navigate")

    def test_allowed_characters_are_left_alone(self):
        self.assertEqual(wire_name("my-server_tool2"), "my-server_tool2")

    def test_other_invalid_characters_are_replaced(self):
        # Server names come from user config, so dots are not the only risk.
        self.assertEqual(wire_name("my server:v1.do it"), "my_server_v1_do_it")


class TestBuildToolPayload(unittest.TestCase):
    """The payload and the map back to qualified names come from one pass."""

    def test_payload_carries_sanitized_names_and_maps_back(self):
        payload, wire_to_qualified = build_tool_payload([_tool("playwright.browser_navigate")])

        self.assertEqual(payload[0]["function"]["name"], "playwright_browser_navigate")
        self.assertEqual(
            wire_to_qualified["playwright_browser_navigate"], "playwright.browser_navigate"
        )

    def test_description_and_schema_are_passed_through(self):
        payload, _ = build_tool_payload([_tool("time.now")])

        self.assertEqual(payload[0]["function"]["description"], "desc for time.now")
        self.assertEqual(payload[0]["function"]["parameters"], {"type": "object"})

    def test_colliding_names_are_disambiguated(self):
        # "github.list_repos" and "github_list.repos" sanitize alike, and
        # dispatching the wrong one would run a tool the user never approved.
        names = ["github.list_repos", "github_list.repos"]

        payload, wire_to_qualified = build_tool_payload([_tool(n) for n in names])

        wire_names = [entry["function"]["name"] for entry in payload]
        self.assertEqual(len(set(wire_names)), 2)
        self.assertEqual(set(wire_to_qualified.values()), set(names))
        for wire, qualified in wire_to_qualified.items():
            self.assertIn(wire, wire_names)
            self.assertIn(qualified, names)

    def test_suffix_does_not_land_on_a_name_already_taken(self):
        # The suffix is itself a name, so it has to be checked too. Otherwise
        # the map rebinds to the later tool and the payload ships two functions
        # called the same thing, which is the mis-dispatch this guards against.
        names = ["example_com.search_2", "example_com.search", "example.com.search"]

        payload, wire_to_qualified = build_tool_payload([_tool(n) for n in names])

        wire_names = [entry["function"]["name"] for entry in payload]
        self.assertEqual(len(set(wire_names)), 3)
        self.assertEqual(set(wire_to_qualified.values()), set(names))

    def test_no_enabled_tools_yields_empty_payload(self):
        # process_query passes "available_tools or None" to the provider.
        self.assertEqual(build_tool_payload([]), ([], {}))


if __name__ == "__main__":
    unittest.main()
