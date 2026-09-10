"""Tests for ollmcp's own log file."""

import logging
import tempfile
import unittest
from unittest.mock import patch

from mcp_client_for_ollama.utils import client_logs


class TestClientLog(unittest.TestCase):
    """The client's warnings land in the session log instead of on screen."""

    def setUp(self):
        handlers_before = list(client_logs.logger.handlers)
        path_before = client_logs._active_log_path

        def restore():
            for handler in client_logs.logger.handlers[len(handlers_before):]:
                handler.close()
            client_logs.logger.handlers = handlers_before
            client_logs._active_log_path = path_before

        self.addCleanup(restore)

    def test_records_go_to_the_session_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(client_logs, "session_log_dir", return_value=tmp), patch.object(
                client_logs, "prune_old_sessions"
            ):
                client_logs.start_client_log()
                logging.getLogger("mcp_client_for_ollama.utils.streaming").warning("boom")
                with open(client_logs.client_log_path(), encoding="utf-8") as log_file:
                    content = log_file.read()

        self.assertIn("WARNING mcp_client_for_ollama.utils.streaming: boom", content)

    def test_old_session_directories_are_pruned_on_every_run(self):
        # Runs that connect no server never build a log sink, so this is the
        # only chance to clean up after them.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(client_logs, "session_log_dir", return_value=tmp), patch.object(
                client_logs, "prune_old_sessions"
            ) as prune:
                client_logs.start_client_log()

        prune.assert_called_once()

    def test_unwritable_log_directory_is_not_fatal(self):
        handlers_before = list(client_logs.logger.handlers)
        with patch.object(client_logs, "session_log_dir", return_value="/dev/null/nope"):
            client_logs.start_client_log()

        self.assertEqual(client_logs.logger.handlers, handlers_before)
        # Nothing is being recorded, so there is no file to point anyone at.
        self.assertIsNone(client_logs.client_log_path())


if __name__ == "__main__":
    unittest.main()
