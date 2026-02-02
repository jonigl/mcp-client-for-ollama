"""Tests for cleanup race condition with stdio servers.

This test suite verifies that the client can gracefully handle cleanup
even when MCP servers send notifications during the shutdown process.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from contextlib import AsyncExitStack
from mcp_client_for_ollama.client import MCPClient
import pytest


class TestCleanupRaceCondition(unittest.IsolatedAsyncioTestCase):
    """Test suite for stdio server cleanup race conditions."""

    @pytest.mark.xfail
    async def test_cleanup_handles_broken_resource_error(self):
        """Test that cleanup gracefully handles BrokenResourceError during exit."""
        # Note: This fails under Windows-12 via Github Actions:
        #    prompt_toolkit.output.win32.NoConsoleScreenBufferError: No Windows console found.
        #    Are you running cmd.exe?
        client = MCPClient()

        # Mock the exit stack to raise BrokenResourceError on aclose()
        # This simulates the race condition where server sends a message
        # while the client is closing streams
        from anyio.streams.memory import BrokenResourceError

        client.exit_stack = AsyncMock(spec=AsyncExitStack)
        client.exit_stack.aclose = AsyncMock(side_effect=BrokenResourceError())

        # This should not raise an exception
        await client.cleanup()

    async def test_cleanup_with_multiple_sessions(self):
        """Test cleanup with multiple active sessions."""
        client = MCPClient()

        # Create mock sessions
        client.sessions = {
            "server1": {"session": MagicMock()},
            "server2": {"session": MagicMock()},
        }

        client.exit_stack = AsyncMock(spec=AsyncExitStack)
        client.exit_stack.aclose = AsyncMock()

        # Should complete without errors
        await client.cleanup()

        # Verify exit_stack.aclose was called
        client.exit_stack.aclose.assert_called_once()

    async def test_cleanup_handles_generic_exception(self):
        """Test that cleanup handles any exception during resource cleanup."""
        client = MCPClient()

        # Mock exit stack to raise a generic exception
        client.exit_stack = AsyncMock(spec=AsyncExitStack)
        client.exit_stack.aclose = AsyncMock(side_effect=RuntimeError("Event loop is closed"))

        # Should not raise
        await client.cleanup()

    async def test_cleanup_with_no_sessions(self):
        """Test cleanup works when no sessions are active."""
        client = MCPClient()
        client.sessions = {}

        client.exit_stack = AsyncMock(spec=AsyncExitStack)
        client.exit_stack.aclose = AsyncMock()

        # Should complete without errors
        await client.cleanup()

        client.exit_stack.aclose.assert_called_once()


class TestEventLoopCleanup(unittest.TestCase):
    """Test suite for event loop cleanup with subprocess management."""

    def test_event_loop_closes_after_executor_shutdown(self):
        """Test that event loop closes gracefully after executor cleanup.

        This simulates the actual fix where we ensure shutdown_default_executor()
        runs before closing the loop, preventing the 'Event loop is closed' error
        from subprocess __del__ methods.
        """
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Track the order of operations
        operations = []

        async def mock_main():
            """Simulate the main async function."""
            operations.append("main_started")
            # Simulate some async work
            await asyncio.sleep(0.01)
            operations.append("main_completed")

        try:
            # Run the main coroutine
            loop.run_until_complete(mock_main())
            operations.append("run_complete")
        finally:
            try:
                # This is the key part - shutdown executor before closing loop
                loop.run_until_complete(loop.shutdown_default_executor())
                operations.append("executor_shutdown")
                loop.run_until_complete(loop.shutdown_asyncgens())
                operations.append("asyncgens_shutdown")
            finally:
                loop.close()
                operations.append("loop_closed")

        # Verify the order of operations
        self.assertEqual(operations, [
            "main_started",
            "main_completed",
            "run_complete",
            "executor_shutdown",
            "asyncgens_shutdown",
            "loop_closed"
        ])

        # Verify loop is actually closed
        self.assertTrue(loop.is_closed())

    def test_subprocess_cleanup_simulation(self):
        """Test that subprocess cleanup works with proper event loop management.

        This simulates a subprocess being cleaned up during shutdown.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        cleanup_called = []

        async def simulate_subprocess_work():
            """Simulate subprocess-like async work."""
            # Schedule cleanup work in the executor (simulating subprocess cleanup)
            def cleanup_fn():
                cleanup_called.append(True)

            # Run in executor (like subprocess cleanup would)
            await loop.run_in_executor(None, cleanup_fn)
            return "completed"

        try:
            result = loop.run_until_complete(simulate_subprocess_work())
            self.assertEqual(result, "completed")
        finally:
            try:
                # Key: shutdown executor waits for pending work to complete
                loop.run_until_complete(loop.shutdown_default_executor())
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

        # Verify cleanup was called
        self.assertTrue(cleanup_called, "Subprocess cleanup should have been called")

    def test_event_loop_error_without_executor_shutdown(self):
        """Test that demonstrates the problem when executor isn't shut down.

        This shows why the fix was necessary by demonstrating what happens
        without proper executor shutdown (though we can't easily trigger the
        actual RuntimeError in a test).
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def quick_work():
            await asyncio.sleep(0.001)

        loop.run_until_complete(quick_work())

        # Without shutting down the executor first, any pending executor tasks
        # would try to schedule on a closed loop. We verify the loop state:
        self.assertFalse(loop.is_closed(), "Loop should not be closed yet")

        # Proper shutdown
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

        self.assertTrue(loop.is_closed(), "Loop should be closed after proper shutdown")


if __name__ == "__main__":
    unittest.main()
