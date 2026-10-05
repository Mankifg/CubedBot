import io
import os
import unittest
from unittest.mock import patch

from src.database_logging import (
    DatabaseLogSink,
    TeeLogStream,
    database_logging_enabled,
    infer_level,
)


class FakeQuery:
    def __init__(self, calls, kind, payload=None):
        self.calls = calls
        self.kind = kind
        self.payload = payload

    def insert(self, rows, returning=None):
        self.calls.append(("insert", rows, returning))
        return self

    def execute(self):
        self.calls.append(("execute", self.kind))
        return {"data": []}


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return FakeQuery(self.calls, "table")

    def rpc(self, name):
        self.calls.append(("rpc", name))
        return FakeQuery(self.calls, "rpc")


class DatabaseLoggingTests(unittest.TestCase):
    def test_database_logging_is_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(database_logging_enabled())

    def test_database_logging_can_be_explicitly_disabled(self):
        with patch.dict(os.environ, {"DATABASE_LOGGING_ENABLED": "0"}, clear=True):
            self.assertFalse(database_logging_enabled())

    def test_level_is_derived_without_changing_message(self):
        self.assertEqual(infer_level("[ERROR] failed", "stdout"), "ERROR")
        self.assertEqual(infer_level("[WARN] retry", "stdout"), "WARN")
        self.assertEqual(infer_level("traceback line", "stderr"), "ERROR")
        self.assertEqual(infer_level("Loaded 20 cogs", "stdout"), "INFO")

    def test_tee_preserves_terminal_output_and_queues_complete_lines(self):
        original = io.StringIO()
        rows = []
        sink = type("Sink", (), {"enqueue": lambda _self, line, stream: rows.append((line, stream))})()
        stream = TeeLogStream(original, sink, "stdout")

        stream.write("first")
        stream.write(" line\nsecond line\n")

        self.assertEqual(original.getvalue(), "first line\nsecond line\n")
        self.assertEqual(rows, [
            ("first line", "stdout"),
            ("second line", "stdout"),
        ])

    def test_sink_uses_minimal_insert_and_limited_prune_rpc(self):
        client = FakeClient()
        sink = DatabaseLogSink(client, io.StringIO())
        rows = [{"message": "hello"}]

        sink._insert(rows)
        sink._prune()

        self.assertIn(("table", "bot_logs"), client.calls)
        self.assertIn(("insert", rows, "minimal"), client.calls)
        self.assertIn(("rpc", "prune_bot_logs"), client.calls)


if __name__ == "__main__":
    unittest.main()
